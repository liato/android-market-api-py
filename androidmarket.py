import base64
import gzip
import pprint
import StringIO
import urllib
import urllib2

from google.protobuf import descriptor
from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

import market_proto

class LoginError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class RequestError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class MarketSession(object):
    SERVICE = "android";
    URL_LOGIN = "https://www.google.com/accounts/ClientLogin"
    ACCOUNT_TYPE_GOOGLE = "GOOGLE"
    ACCOUNT_TYPE_HOSTED = "HOSTED"
    ACCOUNT_TYPE_HOSTED_OR_GOOGLE = "HOSTED_OR_GOOGLE"
    PROTOCOL_VERSION = 2
    authSubToken = None
    context = None

    def __init__(self):
        self.context = market_proto.RequestContext()
        self.context.unknown1 = 0
        self.context.version = 1002012
        self.context.androidId = "0123456789123456"
        self.context.userLanguage = "en"
        self.context.userCountry = "US"
        self.context.deviceAndSdkVersion = "crespo:10"
        self.setOperatorTMobile()

    def _toDict(self, protoObj):
        iterable = False
        if isinstance(protoObj, RepeatedCompositeFieldContainer):
            iterable = True
        else:
            protoObj = [protoObj]
        retlist = []
        for po in protoObj:
            msg = dict()
            for fielddesc, value in po.ListFields():
                #print value, type(value), getattr(value, '__iter__', False)
                if fielddesc.type == descriptor.FieldDescriptor.TYPE_GROUP or isinstance(value, RepeatedCompositeFieldContainer):
                    msg[fielddesc.name.lower()] = self._toDict(value)
                else:
                    msg[fielddesc.name.lower()] = value
            retlist.append(msg)
        if not iterable:
            if len(retlist) > 0:
                return retlist[0]
            else:
                return None
        return retlist

    def setOperatorSimple(self, alpha, numeric):
        self.setOperator(alpha, alpha, numeric, numeric);

    def setOperatorTMobile(self):
        self.setOperatorSimple("T-Mobile", "310260")

    def setOperatorSFR(self):
        self.setOperatorSimple("F SFR", "20810")

    def setOperatorO2(self):
        self.setOperatorSimple("o2 - de", "26207")

    def setOperatorSimyo(self):
        self.setOperator("E-Plus", "simyo", "26203", "26203")

    def setOperatorSunrise(self):
        self.setOperatorSimple("sunrise", "22802")

    def setOperator(self, alpha, simAlpha, numeric, simNumeric):
        self.context.operatorAlpha = alpha
        self.context.simOperatorAlpha = simAlpha
        self.context.operatorNumeric = numeric
        self.context.simOperatorNumeric = simNumeric

    def setAuthSubToken(self, authSubToken):
        self.context.authSubToken = authSubToken
        self.authSubToken = authSubToken

    def login(self, email, password, accountType = ACCOUNT_TYPE_HOSTED_OR_GOOGLE):
        params = {"Email": email, "Passwd": password, "service": self.SERVICE,
                  "accountType": accountType}
        try:
            data = urllib2.urlopen(self.URL_LOGIN, urllib.urlencode(params)).read()
            data = data.split()
            params = {}
            for d in data:
                k, v = d.split("=")
                params[k.strip().lower()] = v.strip()
            if "auth" in params:
                self.setAuthSubToken(params["auth"])
            else:
                raise LoginError("Auth token not found.")
        except urllib2.HTTPError, e:
            if e.code == 403:
                data = e.fp.read().split()
                params = {}
                for d in data:
                    k, v = d.split("=", 1)
                    params[k.strip().lower()] = v.strip()
                if "error" in params:
                    raise LoginError(params["error"])
                else:
                    raise LoginError("Login failed.")
            else:
                raise e

    def execute(self, request):
        request.context.CopyFrom(self.context)
        try:
            headers = {"Cookie": "ANDROID="+self.authSubToken,
                       "User-Agent": "Android-Market/2 (sapphire PLAT-RC33); gzip",
                       "Content-Type": "application/x-www-form-urlencoded",
                       "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7"}
            data = request.SerializeToString()
            data = "version=%d&request=%s" % (self.PROTOCOL_VERSION, base64.b64encode(data))
            request = urllib2.Request("http://android.clients.google.com/market/api/ApiRequest",
                                      data, headers)
            data = urllib2.urlopen(request).read()
            data = StringIO.StringIO(data)
            gzipper = gzip.GzipFile(fileobj=data)
            data = gzipper.read()
            response = market_proto.Response()
            response.ParseFromString(data)
            return response
        except Exception, e:
            raise RequestError(e)

    def searchApp(self, query, startIndex = 0, entriesCount = 10, extendedInfo = True):
        appsreq = market_proto.AppsRequest()
        appsreq.query = query
        appsreq.startIndex = startIndex
        appsreq.entriesCount = entriesCount
        appsreq.withExtendedInfo = extendedInfo
        request = market_proto.Request()
        request.requestgroup.add(appsRequest = appsreq)
        response = self.execute(request)
        retlist = []
        for rg in response.responsegroup:
            if rg.HasField("appsResponse"):
                for app in rg.appsResponse.app:
                    retlist.append(self._toDict(app))
        return retlist

    def getComments(self, appid, startIndex = 0, entriesCount = 10):
        req = market_proto.CommentsRequest()
        req.appId = appid
        req.startIndex = startIndex
        req.entriesCount = entriesCount
        request = market_proto.Request()
        request.requestgroup.add(commentsRequest = req)
        response = self.execute(request)
        retlist = []
        for rg in response.responsegroup:
            if rg.HasField("commentsResponse"):
                for comment in rg.commentsResponse.comments:
                    retlist.append(self._toDict(comment))
        return retlist

    def getImage(self, appid, imageid = "0", imagetype = market_proto.GetImageRequest.SCREENSHOT):
        req = market_proto.GetImageRequest()
        req.appId = appid
        req.imageId = imageid
        req.imageUsage = imagetype
        request = market_proto.Request()
        request.requestgroup.add(imageRequest = req)
        response = self.execute(request)
        for rg in response.responsegroup:
            if rg.HasField("imageResponse"):
                return rg.imageResponse.imageData

    def getCategories(self):
        req = market_proto.CategoriesRequest()
        request = market_proto.Request()
        request.requestgroup.add(categoriesRequest = req)
        response = self.execute(request)
        retlist = []
        for rg in response.responsegroup:
            if rg.HasField("categoriesResponse"):
                for cat in rg.categoriesResponse.categories:
                    retlist.append(self._toDict(cat))
        return retlist

    def getSubCategories(self, apptype):
        req = market_proto.SubCategoriesRequest()
        req.appType = apptype
        request = market_proto.Request()
        request.requestgroup.add(subCategoriesRequest = req)
        response = self.execute(request)
        retlist = []
        for rg in response.responsegroup:
            if rg.HasField("subCategoriesResponse"):
                for cat in rg.subCategoriesResponse.category:
                    retlist.append(self._toDict(cat))
        return retlist

if __name__ == "__main__":
    print "No command line interface available, yet."
