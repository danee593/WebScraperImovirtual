import sys
import math
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd


# Constants
BROWSER_HEADER: dict = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5)"\
                        " AppleWebKit/537.36 (KHTML, like Gecko)"\
                        " Chrome/50.0.2661.102 Safari/537.36"}
TIME_OUT: int = 10


def main():
    ## Keep in mind that you are still not implementing the ALL function.
    try:
        announcements_to_scrape = number_of_announcements(sys.argv)
    except ValueError:
        sys.exit()
    try:
        main_urls = imovirtual_url_generator(announcements_to_scrape)
    except ValueError:
        sys.exit("Announcements should be greater than zero.")
    all_announcement_urls = all_announcements_urls(main_urls, announcements_to_scrape)
    cleaned_data = extract_and_transform_announcement_urls(all_announcement_urls)
    df = pd.DataFrame(cleaned_data)
    try:
        df.to_excel('inmovirtual.xlsx', index = False)
    except PermissionError:
        sys.exit("Please close the file, and try again")
    return 0


def number_of_announcements(argument_list: list) -> int:
    '''
    This function scans the command line arguments to find how many announcements
    the user wants to scrape.
    The function has been type hinted: param 1 is expected to be a list.

    :param argument_list: this list will be used to verify the length
    and the contents.
    :returns: The function returns a number between 1 and 50000 inclusive,
    depending on how many annoucements the user wants to scrape, if the user
    wants to scrape all arguments it returns -1.
    :raises ValueError: this function has code that raises a ValueError when user
    does not cooperate on usage.
    '''
    help_message:str = "Scrapes announcements of appartments for sell in Portugal\n" \
        "Please note that you might get less announcements than you selected.\n" \
        "Usage: prototype [options]\n" \
        "Options:\n" \
        "   -n 0>int<50000, The number of announcements to scrape\n" \
        "   -n ALL, to scrape all of the announcements" \
        "   -h, --help Display this help message\n"
    if len(argument_list) == 1:
        print(help_message)
        raise ValueError
    elif len(argument_list) == 2 and argument_list[1] in ("-h", "--help"):
        print(help_message)
        raise ValueError
    elif len(argument_list) == 3 and argument_list[1] == "-n":
        if argument_list[2] == "ALL":
            return -1
        else:
            try:
                n_of_announcements: int = int(argument_list[2])
                if n_of_announcements <= 0:
                    print(help_message)
                    raise ValueError
                return n_of_announcements
            except ValueError:
                raise ValueError
    else:
        raise ValueError


def imovirtual_url_generator(no_announcements: int,
                             base_url: str = "https://www.imovirtual.com/"\
                            "comprar/apartamento/") -> list:
    announcements_per_page: int = 72
    if no_announcements <= 0 or announcements_per_page <= 0:
        raise ValueError
    main_urls_index: int = math.ceil(no_announcements / announcements_per_page)
    imovirtual_main_urls: list = []
    for index in range(1, main_urls_index + 1):
        main_url_with_index: str = f"{base_url}?nrAdsPerPage={announcements_per_page}&page={index}"
        imovirtual_main_urls.append(main_url_with_index)
    return imovirtual_main_urls


def client_request(url_to_query: str, header:str = BROWSER_HEADER, timeout:int = TIME_OUT) -> str:
    try:
        response: str = requests.get(url = url_to_query, headers = header, timeout = timeout)
    except requests.exceptions.RequestException:
        response: str = None
    if response.status_code == 200:
        response: str = response.text
    else:
        response: str = None
    return response


def get_postal_code(latitude: str, longitude: str) -> str:
    street_map_url = "https://nominatim.openstreetmap.org/reverse?" \
        f"lat={latitude}&lon={longitude}&format=json"
    response = client_request(street_map_url, header = None)
    if response is not None:
        response_dict_format: dict = json.loads(response)
        try:
            response: str = response_dict_format["address"]["postcode"]
        except KeyError:
            response: str = None
        return response
    else:
        return response


def extract_announcement_urls_from_main_url(response: str) -> list:
    list_announcement_urls = []
    soup = BeautifulSoup(response, "html.parser")
    elements_with_data_url = soup.find_all(attrs={"data-url": True})
    if len(elements_with_data_url) == 0:
        return None
    for element in elements_with_data_url:
        list_announcement_urls.append(element["data-url"])
    return list_announcement_urls


def all_announcements_urls(main_urls: list, user_no_announcements: int) -> list:
    all_announcement_urls_list = []
    for urls in main_urls:
        main_url_html = client_request(urls)
        if main_url_html is None: #Request failed then continue with the next one
            continue
        announcement_urls = extract_announcement_urls_from_main_url(main_url_html)
        if announcement_urls is None: #No attrs "data-url"
            continue
        all_announcement_urls_list += announcement_urls
    return all_announcement_urls_list[:user_no_announcements]


def extract_script_from_announcement_url(response_text: str) -> dict:
    soup = BeautifulSoup(response_text, "html.parser")
    script_element = soup.find("script", id = "__NEXT_DATA__")
    try:
        script_content = script_element.contents[0]
    except IndexError:
        return None
    try:
        script_element = json.loads(script_content)
        return script_element
    except json.JSONDecodeError:
        return None


def extract_main_keys(script: dict) -> tuple:
    try:
        ad_data = script["props"]["pageProps"]["ad"]
        location_data = ad_data["location"]
        target_data = ad_data["target"]
        return ad_data, location_data, target_data
    except (KeyError,TypeError):
        raise ValueError


def extract_primary_info(required_keys: list, dictionary_to_verify: dict) -> dict:
    primary_data = {}
    if all([key in dictionary_to_verify for key in required_keys]):
        for key in required_keys:
            primary_data[key] = dictionary_to_verify[key]
        return primary_data
    else:
        return None


def target_info_extract(target_dict: dict) -> dict:
    target_data = {}
    try:
        for key in target_dict:
            i = 0
            if key in ("AreaRange", "City_id", "MarketType", "ObidoAdvert", "Photo", "RegularUser",
                    "Title", "categoryId", "env", "seller_id"):
                continue
            elif isinstance(target_dict[key],list):
                if len(target_dict[key]) == 1:
                    target_data[key] = target_dict[key][0]
                else:
                    for item in target_dict[key]:
                        target_data[f"{key}_{i}"] = item
                        i += 1
            else:
                target_data[key] = target_dict[key]
        return target_data
    except (KeyError,TypeError):
        raise ValueError


def location_info_extract(location_data: dict) -> dict:
    location_info = {}
    try:
        location_info["street_name"] = location_data["address"]["street"]["name"]
        location_info["street_number"] = location_data["address"]["street"]["number"]
        location_info["subdistrict"] = location_data["address"]["subdistrict"]
        location_info["district"] = location_data["address"]["district"]
        location_info["city_name"] = location_data["address"]["city"]["name"]
        location_info["municipality"] = location_data["address"]["municipality"]
        location_info["county"] = location_data["address"]["county"]["name"]
        location_info["province"] = location_data["address"]["province"]["name"]
        location_info["postalCode"] = location_data["address"]["postalCode"]
        return location_info
    except (KeyError, TypeError):
        return None


def json_script_processing(script: dict) -> dict:
    announcement_data = {}
    try:
        ad_data, location_data, target_data = extract_main_keys(script = script)
    except ValueError:
        return None
    ad_required_keys = ["modifiedAt", "description"]
    ad_information = extract_primary_info(ad_required_keys, ad_data)
    location_required_keys = ["latitude", "longitude"]
    location_information = extract_primary_info(location_required_keys, location_data["coordinates"])
    if ad_information is None or location_information is None:
        return None
    announcement_data.update(ad_information)
    announcement_data.update(location_information)
    announcement_data["PostalCodeAPI"] = get_postal_code(announcement_data["latitude"],
                                                          announcement_data["longitude"])
    try:
        target_information = target_info_extract(target_data)
        announcement_data.update(target_information)
    except ValueError:
        return None
    location_information_extended = location_info_extract(location_data)
    if location_information_extended is not None:
        announcement_data.update(location_information_extended)
    return announcement_data


def extract_and_transform_announcement_urls(announcement_urls_to_process: list) -> list:
    announcement_features = []
    for url_announcement in announcement_urls_to_process:
        annoucement_html: str = client_request(url_announcement)
        if annoucement_html is None:
            continue
        annoucement_script = extract_script_from_announcement_url(annoucement_html)
        if annoucement_script is None:
            continue
        announcement_processed = json_script_processing(annoucement_script)
        announcement_features.append(announcement_processed)
    return announcement_features


if __name__ == "__main__":
    main()
