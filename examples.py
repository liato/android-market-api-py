from pprint import pprint

import market_proto
from androidmarket import MarketSession

if __name__ == "__main__":
    # Start a new session and login
    session = MarketSession()
    session.login("user@gmail.com", "password")

    # Search for "bankdroid" on the market and print the first result
    results = session.searchApp("bankdroid")
    if len(results) == 0:
        print "No results found"
        exit()

    app = results[0]
    pprint(app)

    # Print the last two comments for the app
    results = session.getComments(app["id"])
    pprint(results[:2])

    # Download and save the first screenshot
    data = session.getImage(app["id"])
    f = open("screenshot.png", "wb")
    f.write(data)
    f.close()

    # Download and save the app icon
    data = session.getImage(app["id"], imagetype=market_proto.GetImageRequest.ICON)
    f = open("icon.png", "wb")
    f.write(data)
    f.close()

    # Get all the categories and subcategories
    results = session.getCategories()
    pprint(results)
