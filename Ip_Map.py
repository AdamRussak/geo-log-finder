##Pip needed:
# pip3 install mariadb
#packages for location form IP  process
import json
from typing import Counter, Mapping
from datetime import datetime 
#push to MariaDB - grafana talbe:
import mariadb
import sys
import os
## module to check if IP is private
import ipaddress
import time
from loguru import logger
import requests

## Env vars to use in Task:
v_accesLogs = os.getenv('logLocation')
v_user = os.getenv('dbUser')
v_password = os.getenv('dbPass')
v_host = os.getenv('dbHost')
v_port = os.getenv('dbPort')
v_database = os.getenv('dbName')
v_dbTable = os.getenv('dbTable')
v_dbBaseUrl = os.getenv('geoIpUrl')
v_sleepTime = os.getenv('sleepTime')
# func to check list of ip already in it or not
def checkDuplicate(list, listValue, jsonInput, jsonInputValue):
    if len(list) == 1:
        return False
    else:
        for find in list:
            if find[listValue] == jsonInput[jsonInputValue]:
                return True
        return False
def checkDuplicateFinal(list, listValue, jsonInput, jsonInputValue):
    for listing in jsonInput:
        a = "new"
        if list[listValue] == listing[jsonInputValue] and list['timeStamp'] == listing['timeStamp']:
            a = "pass"
            break
    for listing in jsonInput:
        if list[listValue] == listing[jsonInputValue] and a == False:
            a = "update"
            break
    return a
while True:
# Opening Log file and convert to JSON file
    logger.info("Starting Run...")
    f = open(v_accesLogs)
    num_lines = sum(1 for line in open(v_accesLogs))
    arryJson = "["
    counter = 0
    for row in f:
        counter = counter+1
        if counter < num_lines:
            arryJson += str(row)+","
        else:
            arryJson += str(row)
    
    arryJson += "]"
    f.close()
    try:
        data = json.loads(arryJson)
        logger.info("Got " + str(counter) + " Access Log Rows")
    except:
        logger.error("Error Loading the Logs")
    jsonList = []
    for i in data:
        if not ipaddress.ip_address(str(i['ClientHost']) ).is_private:
            if i['ClientHost'] != 'localhost' or i['RequestPath'] != '/System/Ping':
                if not checkDuplicate(jsonList, 'ip', i,'ClientHost'):
                    iIP = i['ClientHost']
                    date = datetime.strptime(i['time'], "%Y-%m-%dT%H:%M:%SZ") 
                    featchDate = date.strftime("%Y-%m-%d") 
                    timeStamp = date.strftime("%Y-%m-%d %H:%m:%S") 
                    inputRow = {"ip":iIP,"featchDate": featchDate, "timeStamp": timeStamp}
                    dump = json.dumps(inputRow)
                    jsonList.append(json.loads(dump))
    logger.info("Inspecting " + str(len(jsonList)) + " IP's Out of " + str(counter) + " Access Log Rows")
    # Connect to MariaDB Platform
    try:
        conn = mariadb.connect(
            user = v_user,
            password = v_password,
            host = v_host,
            port = int(v_port),
            database = v_database
        )
        cur = conn.cursor()
        logger.info("Successfully connected to database")
    except mariadb.Error as e:
        logger.debug("Unable to create List from response " + e)
        sys.exit(1)

    ## create List of ips from otput 'jsonList
    listOfIps = []
    if len(jsonList) > 0:
        for ip in jsonList:
            listOfIps.append(ip['ip'])

    ## if block for UPdate output of create of list need to be checked with freeGeoIP
    logger.info("Trying to Get " + str(len(listOfIps)) + " IP's from DB")
    if len(listOfIps) > 0:
        format_strings = ','.join(['%s'] * len(listOfIps))
        cur.execute(
            "SELECT * FROM " + v_dbTable + " WHERE clientIP IN (%s)" % format_strings,
                        tuple(listOfIps))
        row_headers = [x[0] for x in cur.description] #this will extract row headers
        rv = cur.fetchall()
        json_data = []
        for result in rv:
            json_data.append(dict(zip(row_headers,result)))
        dbResult = json.dumps(json_data, indent=4, sort_keys=True, default=str)
        dbResult = json.loads(dbResult)
    lst = []
    ipInfoList = []
    # 
    ## ipinfo task 
    logger.info("Got " + str(len(dbResult)) + " Results from DB")
    if len(dbResult) > 0:
        for ip in jsonList:
            # add data from DB and arrange to a list.
            isListed = checkDuplicateFinal(ip, 'ip', dbResult, 'clientIP')
            if isListed == "update":
                for listing in dbResult:
                    if ip['ip'] == listing['clientIP'] and ip['ip'] not in lst:
                        logger.info("Updating record for " + str(ip['ip']))
                        lst.append(listing['clientIP'])
                        lst.append(listing['clientState'])
                        lst.append(listing['ClientCity'])
                        lst.append(listing['ClientLatitude'])
                        lst.append(listing['ClientLongitude'])
                        lst.append(ip['featchDate'])
                        lst.append(ip['timeStamp'])
                        logger.info("Got " + str(len(lst)) + " Records from DB")
            elif isListed == "new" and ip['ip'] not in ipInfoList:
                ipInfoList.append(ip['ip'])
                logger.info("Adding to new record list: " + str(ip['ip']))
    else:
        logger.info("All New IP's")
        logger.info("Adding all " + str(len(jsonList)) + " Records to FreeGeoIp Call")
        for ip in jsonList:
            ipInfoList.append(ip['ip'])
    if len(ipInfoList) > 0:
        logger.info("Starting process to get " + str(len(ipInfoList)) + " IP's Results from FreeGeoIp")
        for ip in ipInfoList:
            logger.info("Checking " + str(ip) + " in FreeGeoIp")
            response = requests.get(v_dbBaseUrl + "/json/" + ip)
            response = response.json()
            if ip == response['ip'] and ip not in lst:
                logger.info("New Records for " + str(ip))
                lst.append(response['ip'])
                lst.append(response['country_name'])
                lst.append(response['city'])
                lst.append(str(response['latitude']))
                lst.append(str(response['longitude']))
                for attrs in jsonList:
                    if attrs['ip'] == ip and attrs['timeStamp'] not in lst[len(lst) - 1]:
                        lst.append(attrs['featchDate'])
                        lst.append(attrs['timeStamp'])
    if len(lst) > 0:
        lst_tuple = [x for x in zip(*[iter(lst)]*7)]
        logger.info("Adding " + str(len(lst_tuple)) + " Records to MariaDB")
        logger.info("Start Uploading results to DB")
        ##worke mysql push regestry
        try:
            cur = conn.cursor()
            cur.executemany("INSERT INTO " + v_dbTable + " (clientIP,clientState,ClientCity,ClientLatitude,ClientLongitude,featchDate,timeStamp) VALUES (%s, %s, %s, %s, %s, %s, %s)", lst_tuple)
            conn.commit()
            conn.close()
            logger.info("Records Updated Succesfully")
        except mariadb.Error as e:
            logger.debug("Unable to Insert List from response " + e)
            sys.exit(1)
    else:
        logger.info("No Records to Update")
    logger.info("End Run...")
    logger.info("Start SLEEP " + str(v_sleepTime) + " Seconds")
    time.sleep(float(v_sleepTime))