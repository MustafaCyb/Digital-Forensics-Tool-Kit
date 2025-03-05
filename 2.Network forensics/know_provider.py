import geoip2.database
import platform

def get_ip_info(ip):
    
    try:
        if platform.system() == "Windows":
            Database = "DataBase\\GeoLite2-City.mmdb"
        else:
            Database = "DataBase/GeoLite2-City.mmdb"
        with geoip2.database.Reader(Database) as reader:
            response = reader.city(ip)
            ip_info = {
                'Country': response.country.name,
                'Region': response.subdivisions.most_specific.name,
                'City': response.city.name,
                'Location': f"{response.location.latitude}, {response.location.longitude}",
                'Organization': response.traits.isp
            }
            return ip_info
    except Exception as e:
        return {'Error': str(e)}


