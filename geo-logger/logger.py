import json,ipaddress,time,requests
import mysql.connector
from loguru import logger
from ipinfo import ipinfo

v_accesLogs = 'traefik.json'   #os.getenv('_LOG_PATH')
v_user = 'grafana'#os.getenv('_APP_DB_USER')
v_password = 'T0mer!2405-77'#os.getenv('_APP_DB_PASS')
v_host = '192.168.0.252'#os.getenv('_APP_DB_HOST')
v_port = 3306#os.getenv('_APP_DB_PORT')
v_database = 'grafana' #os.getenv('_GRAFANA_DB_SCHEMA')
v_dbTable = 'grafana' #os.getenv('_GRAFANA_DB_TABLE')
v_geoIPUrl = 'https://geo.techblog.co.il' #os.getenv('_GEO_IP_URL')
v_sleepTime = 15# os.getenv('_SLEEP_TIME')

#Get ip info from GeoIP service
def get_ip_info(ip):
    try:
        logger.info("Getting IP info for IP: {}".format(ip))
        response = requests.get(v_geoIPUrl + "/json/" + ip)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        logger.error(e)
        return None

#Read Traefik logs
def read_log_file(file_name):
    try:
        logger.info("Reading log file: {}".format(file_name))
        with open(file_name, 'r') as f:
            log = f.readlines()
            logger.info("Number of lines: {}".format(len(log)))
            return log
    except Exception as e:
        logger.error(e)
        return None

def parse_log_file(log):
    try:
        logger.info("Parsing log file")
        list = []
        for line in log:
            data = json.loads(line)
            ip = data['ClientHost']
            timestamp = data['time'].replace('T', ' ').replace('Z', '')
            featchDate = time.strftime("%Y-%m-%d")
            if ipaddress.ip_address(ip).is_private or record_exists(ip, timestamp):
                continue
            geo_info = get_ip_info(ip)
            if geo_info is not None:
               list.append(ipinfo(clientIP=ip, clientState=geo_info['country_name'], ClientCity=geo_info['city'],ClientLatitude=geo_info['latitude'],ClientLongitude=geo_info['longitude'],featchDate=featchDate,timeStamp=timestamp))
        logger.info("Number of new records: {}".format(len(list)))
        return list
    except Exception as e:
        logger.error(e)
        return None


def record_exists(ip, timeStamp):
    try:
        cnx = mysql.connector.connect(user=v_user, password=v_password, host=v_host, port=v_port, database=v_database,charset='ascii', use_unicode=True)
        cursor = cnx.cursor()
        query = "SELECT * FROM " + v_dbTable + " WHERE clientIP = %s AND timeStamp = %s"
        cursor.execute(query, (ip, timeStamp))
        cursor.fetchall()
        if cursor.rowcount > 0:
            cursor.close()
            cnx.close()
            return True
        else:
            cursor.close()
            cnx.close()
            return False
    except Exception as e:
        logger.error(str(e))
        return None
    
def insert_to_db(list):
    try:
        logger.info("Inserting to DB")
        cnx = mysql.connector.connect(user=v_user, password=v_password, host=v_host, port=v_port, database=v_database,charset='ascii', use_unicode=True)
        cursor = cnx.cursor()
        for item in list:
            query = "INSERT INTO " + v_dbTable + " (clientIP, clientState, ClientCity, ClientLatitude, ClientLongitude, featchDate, timeStamp) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (item.clientIP, item.clientState, item.ClientCity, item.ClientLatitude, item.ClientLongitude, item.featchDate, item.timeStamp))
        cnx.commit()
        cursor.close()
        cnx.close()
    except Exception as e:
        logger.error(e)
        return None

def main():
    try:
        logger.info("Starting logger")
        log = read_log_file(v_accesLogs)
        list = parse_log_file(log)
        insert_to_db(list)
    except Exception as e:
        logger.error(e)
        

if __name__ == '__main__':
    while (True):
        main()
        time.sleep(int(v_sleepTime))
