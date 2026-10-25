from bs4 import BeautifulSoup
import requests
import os
import json

# results_d = {}
# pages_d = {}


os.makedirs("scraping/scraped_files",exist_ok=True)

# for i in range(1,6):
    # pages_d["url{0}".format(i)] = f"https://stetoskop.info/aktuelno?page={i}"
    # results_d["result{0}".format(i)] = requests.get(pages_d[f"url{i}"]) # in dict you acces through key..
    #for download i needed that results dict
             # with open(f"scraping/scraped_files/page{i}.html","w",encoding="utf-8")as f:
             #     f.write(results_d[f"result{i}"].text)

soups = []

for i in range(1,6):
    with open(f"scraping/scraped_files/page{i}.html", "r", encoding = "utf-8") as f :
        soups.append(BeautifulSoup(f,"html.parser"))


# for i in range(1,3):
#     print(f"skripta{i}")
#     print(soup_d[f"soup{i}"].prettify())









classNameTitle = "after:absolute after:inset-0 after:rounded-2xl after:content-[''] focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-brand"
classNameText = "mt-1.5 line-clamp-2 text-base leading-5.25 text-ink dark:text-slate-300"

#gluplji nacin..
    # tags_d = {} 
    # texts_d = {}
    # for i in range(1,6):
    #     tags_d[f"tag{i}"] = soup_d[f"soup{i}"].find_all("a", class_ = classNameTitle)
    #     texts_d[f"text{i}"] = soup_d[f"soup{i}"].find_all("p", class_ = classNameText)



tags = []
texts = []

for soup in soups:
    tags.append(soup.find_all("a" , class_ = classNameTitle))
    texts.append(soup.find_all("p" , class_ = classNameText))




json_list = []
count = 1
for i in range(len(tags)):  #tags[i] list of links from page i
    for j in range(len(tags[i])): #tags[i][j] every link individually from the page
        title = tags[i][j].get_text(strip = True)
        link = tags[i][j]['href']
        text = texts[i][j].get_text(strip = True)
        print(f"Title {count}:{title}")
        print(f"Link:{link}")
        print(f"Text:{text} \n \n")


        json_article = {
            'title' : title,
            'link' : link,
            'text' : text
        }

        json_list.append(json_article)
        count+=1


os.makedirs("scraping/json", exist_ok=True)
with open("scraping/json/articles.json", "w",encoding= 'utf-8') as f:
    json.dump(json_list,f,indent=4,ensure_ascii=False)