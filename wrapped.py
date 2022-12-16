"""Modified from https://github.com/kanashter/bothermione-ao3wrapped
"""

import datetime
import itertools
import json
import os

import bs4
import pandas
import requests


YEAR = 2022
N_TOP = 10


class InvalidUserOrPasswordError(Exception):
    pass


def return_session(username, password):
    s = requests.Session()
    payload = {
        "utf8": "%E2%9C%93",
        "user[login]": username,
        "user[password]": password,
        "commit": "Log+In"
    }
    site = s.get("https://archiveofourown.org")
    soup = bs4.BeautifulSoup(site.content, 'html.parser')
    payload["authenticity_token"] = soup.find("input", {"name": "authenticity_token"})['value']

    s.encoding = 'utf-8'
    s.post("https://archiveofourown.org/users/login", data=payload)
    return s

def get_pages(base_url, session):
    request = session.get(base_url)
    soup = bs4.BeautifulSoup(request.content, 'html.parser')

    error_flash = soup.find("div", {"class": "flash error"})
    if error_flash is not None:
        error_msg = error_flash.text
        raise InvalidUserOrPasswordError(error_msg)
    
    pages = soup.find("ol", { "class": "pagination actions" })
    all_pages = []
    for li in pages.findAll('li'):
        all_pages.append(li.text)
    max_pages = int(all_pages[-2])
    return [*range(1, max_pages+1)]

def get_fics(base_url, session):
    request = session.get(base_url)
    soup = bs4.BeautifulSoup(request.content, 'html.parser')
    works = soup.find("ol", { "class": "reading work index group" })
    all_fics = []
    fics = works.findChildren("li", recursive=False)
    for i in fics:
        try:
            temp_fic = fic_check(i)
            if temp_fic['dt'] >= datetime.datetime(YEAR, 1, 1, 0, 0):
                all_fics.append(temp_fic)
            else:
                break
        except:
            pass

    return all_fics

def fic_check(soup):
    title_array = []
    character_array = []
    freeform_array = []

    heading = soup.find("h4", { "class": "heading"})
    title_details = heading.findChildren("a", recursive=False)
    for i in title_details:
        title_array.append(i.text)
    try:
        relationships = [x.text for x in soup.findAll("li", { "class": "relationships" })]
    except:
        relationships = None
    characters = soup.findAll("li", { "class": "characters" })
    for i in characters:
        character_array.append(i.text)

    freeforms = soup.findAll("li", { "class": "freeforms"})
    for i in freeforms:
        freeform_array.append(i.text)

    visited = soup.find("h4", { "class": "viewed heading" }).text.replace('\n', '').replace(',', '')
    visited_list = visited.split()
    visited_count = visited_list[visited_list.index("Visited") + 1]
    if visited_count == "once":
        visited_count = 1
    else:
        visited_count = int(visited_count)

    last_visited = (' ').join(visited_list[2:5])
    dt = datetime.datetime.strptime(last_visited, '%d %b %Y')

    word_count = int(soup.find("dd", { "class": "words"}).text.replace(',', ''))

    details = {
        "title": title_array[0],
        "author": title_array[1],
        "relationships": relationships,
        "characters": character_array,
        "word_count": word_count,
        "tags": freeform_array,
        "visited": visited_count,
        "dt": dt
    }
    return details


def load_data(username, password):
    session = return_session(username, password)
    base_url = f"https://archiveofourown.org/users/{username}/readings"
    all_pages = get_pages(base_url, session)
    all_fics = []
    all_breaks = []
    for i in all_pages:
        try:
            fics_url = base_url + f"?page={i}"
            fics = get_fics(fics_url, session)
            for fic in fics:
                all_fics.append(fic)
                if fic["dt"] >= datetime.datetime(YEAR, 1, 1):
                    all_breaks.append(False)
                else:
                    all_breaks.append(True)
        except:
            pass

        if True in all_breaks:
            print(f'BREAKING ON PAGE {i}')
            break

    return all_fics

def resolve_request(username, password):
    
    raw_data = load_data(username, password)
    frame = pandas.DataFrame(raw_data)
    frame["title_author"] = frame["title"] + ' by ' + frame["author"]

    return frame


def analysis(frame, n=N_TOP):

    total_words = frame.word_count.sum()
    total_fics = len(frame)
    total_reads = frame.visited.sum()

    top_titles = list(frame.nlargest(n, ['visited'])[['title_author', 'visited']].itertuples(index=False, name=None))

    top_authors = frame.groupby(['author'])['visited'].sum().nlargest(n)
    top_authors = list(zip(top_authors.index, top_authors))

    top_relationships = pandas.Series(itertools.chain(*frame['relationships'].tolist())).value_counts().head(n)
    top_relationships = list(zip(top_relationships.index, top_relationships))

    top_characters = pandas.Series(itertools.chain(*frame['characters'].tolist())).value_counts().head(n)
    top_characters = list(zip(top_characters.index, top_characters))

    top_tags = pandas.Series(itertools.chain(*frame['tags'].tolist())).value_counts().head(n)
    top_tags = list(zip(top_tags.index, top_tags))

    mv = {
        "titles": top_titles,
        "authors": top_authors,
        "relationships": top_relationships,
        "characters": top_characters,
        "tags": top_tags
    }

    return_data = {
        "total_words": int(total_words),
        "total_fics": int(total_fics),
        "total_reads": int(total_reads),
        "most_visited": mv,
    }

    return return_data


if __name__ == "__main__":

    username = os.environ.get('AO3_USERNAME')
    password = os.environ.get('AO3_PASSWORD')

    data = analysis(resolve_request(username, password))

    with open(f"results_{username}.json", mode="w") as f:
        json.dump(data, f, indent=2)
