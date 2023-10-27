import requests
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
import json
import numpy as np


specialCases = {
    "627e14b21713922ded6f2c15": 250000,
    "634959225289190e5e773b3b": 15000
}


def GetMean(array):
    return np.mean(array)

def GetSTD(array):
    return np.std(array)

def getItemPrice(priceList, handbookItems, itemTpl):
    if not priceList.__contains__(itemTpl):
        for hi in handbookItems:
            if hi["Id"] == itemTpl:
                return hi["Price"]
    return priceList[itemTpl]

def getAveragedPrice(item):
    prices = item["historicalPrices"]
    prices_list = []
    for pr in prices:
        if pr["price"] not in prices_list:
            prices_list.append(pr["price"])
    avgMean = GetMean(prices_list)
    standardDev = GetSTD(prices_list)
    upperCutoff = standardDev * 1.5
    lowerCutoff = standardDev * 2
    lowerBound = avgMean - lowerCutoff
    upperBound = avgMean + upperCutoff
    pricesWithOutliersRemoved = []
    for pr in prices_list:
        if pr >= lowerBound and pr <= upperBound:
            pricesWithOutliersRemoved.append(pr)
    avgPriceWithoutOutliers = round(GetMean(pricesWithOutliersRemoved))
    return avgPriceWithoutOutliers

def processTarkovDevPrices(tarkovDevPrices):
    filteredTarkovDevPrices = {}
    for item in tarkovDevPrices:
        if len(item["historicalPrices"]) == 0:
            continue
        averagedItemPrice = getAveragedPrice(item)
        if averagedItemPrice == 0:
            continue
        
        filteredTarkovDevPrices.update({item["id"] : {
            "Name": item["name"],
            "Average24hPrice": item["avg24hPrice"],
            "Average7DaysPrice": averagedItemPrice,
            "TemplateId": item["id"],
        }})
    return filteredTarkovDevPrices

def processData():
    tarkovprices = json.load(open("tarkovprices.json", encoding="utf-8"))
    handbook = json.load(open("handbook.json", encoding="utf-8"))
    items = json.load(open("items.json", encoding="utf-8"))
    priceList = {}

    filteredTarkovDevPrices = processTarkovDevPrices(tarkovprices)
    for itemId in items:
        if not filteredTarkovDevPrices.__contains__(itemId):
            continue
        itemPrice = filteredTarkovDevPrices[itemId]
        if (itemPrice["Average7DaysPrice"] != 0):
            priceList[itemId] = itemPrice["Average7DaysPrice"]
    ammoPacks = {}
    for itemid in items:
        item = items[itemid]
        if item["_parent"] == "5661632d4bdc2d903d8b456b" or item["_parent"] == "543be5cb4bdc2deb348b4568":
            if item["_name"].__contains__("ammo_box_"):
                if not item["_name"].__contains__("_damaged"):
                    ammoPacks.update({ itemid: item})

    for ammoPackId in ammoPacks:
        ammoPack = ammoPacks[ammoPackId]
        if not priceList.__contains__(ammoPackId):
            itemMultipler = ammoPack["_props"]["StackSlots"][0]["_max_count"]
            singleItemPrice = getItemPrice(priceList, handbook["Items"], ammoPack["_props"]["StackSlots"][0]["_props"]["filters"][0]["Filter"][0])
            price = singleItemPrice * itemMultipler
            priceList.update({ammoPack["_id"] : price})

    for specialCaseId in specialCases:
        specialCasePrice = specialCases[specialCaseId]
        if not priceList.__contains__(specialCaseId):
            priceList.update({specialCaseId : specialCasePrice})

    with open("prices.json","w") as tp:
        tp.write(json.dumps(priceList, indent=4))


def main():

    transport = AIOHTTPTransport(url="https://api.tarkov.dev/graphql")

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)

    # Provide a GraphQL query
    query = gql(
        """
    {
        items(lang: en) {
            id
            name
            avg24hPrice
            changeLast48hPercent
            historicalPrices {
                price
                timestamp
            }
        }
    }
    """
    )

    # Execute the query on the transport
    result = client.execute(query)
    with open("tarkovprices.json","w", encoding="utf-8") as tp:
        tp.write(json.dumps(result["items"], indent=4))
    print("done")

    handbook = requests.get("https://dev.sp-tarkov.com/SPT-AKI/Server/raw/branch/master/project/assets/database/templates/handbook.json")
    with open("handbook.json","w", encoding="utf-8") as tp:
        tp.write(handbook.text)

    items = requests.get("https://dev.sp-tarkov.com/SPT-AKI/Server/raw/branch/master/project/assets/database/templates/items.json")
    with open("items.json","w", encoding="utf-8") as tp:
        tp.write(items.text)

    processData()

main()