import scrapy
import pandas as pd
import numpy as np
from pandas import DataFrame, Series
import json
import os
import requests
import _pickle
import glob


from stem import Signal
from stem.control import Controller



class JagranSpider(scrapy.Spider):
    name = "jagran"
    user_agent = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1"
    story_404 = "404.pkl"
    not_found_stories = []

    def change_ip(self, change):
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password='TopSecret')
            response = requests.get('http://icanhazip.com/', proxies={'http': '127.0.0.1:8118'})        
            print("original ip:", response.text.strip())
            if change:
                controller.signal(Signal.NEWNYM)
                response = requests.get('http://icanhazip.com/', proxies={'http': '127.0.0.1:8118'})        
                print("changing ip to:", response.text.strip())


    def start_requests(self):
        print(os.getcwd())
        df = pd.read_csv("RecSys.tsv", sep="\t")
#        self.change_ip(False)
        df['URL'] = 'https://www.jagran.com'+df.Page
        df['URL']= df.URL.str.split("?").apply(lambda val: val[0])
        df.drop_duplicates('URL', inplace=True)
#        all_files = glob.glob("data/*.json")
        all_files = _pickle.load(open('all_files.pkl', 'wb'))
        request = scrapy.Request(url='http://icanhazip.com/', callback=self.show_ip)
        yield request
        if os.path.exists(self.story_404):
            with open(self.story_404,'rb') as rfp: 
                self.not_found_stories = _pickle.load(rfp)
        for index, row in df.iterrows():	
            filename = 'data/'+str(row['storyID'])+'.json'
            if (not (filename in all_files)) and (not (str(row['storyID']) in self.not_found_stories)):   
                url = row['URL']
                request = scrapy.Request(url=url, callback=self.parse)
                request.meta['story_id'] = str(row['storyID'])
                request.meta['unique_page_views'] = str(row['Unique_Page_Views'])
                request.meta['filename'] = filename
                request.meta['filename'] = filename
                yield request
            else:
                self.log("file already exist {}".format(filename))


            
    def parse(self, response):
        try:
            item = {}
            item['url'] = str(response.url)
            item['story_id'] = response.meta['story_id']
            item['unique_page_views'] = response.meta['unique_page_views']
            item['etitle'] = response.css('title::text').extract_first()
            item['keywords'] = response.css("meta[name=news_keywords]::attr(content)").extract_first()
            item['description'] = response.css("meta[name=description]::attr(content)").extract_first()
            item['modified_date'] = response.css("meta[property='article:modified_date']::attr(content)").extract_first()
            article = response.css("div.articleBody > p")
            body = article[:-1].css("::text").extract()
            body = " ".join(body).replace('\xa0', '')
            item['body'] = " ".join(body.split())
            item['htitle'] = response.css('h1::text').extract_first()
            item['author'] = article[-1].css("strong::text").extract_first()
            data = json.dumps(item)
            with open(response.meta['filename'], 'w') as f:
                f.write(data)
        except IndexError as exc:
            self.not_found_stories.append(item['story_id'])
            with open(self.story_404, "wb") as wfp:
                _pickle.dump(self.not_found_stories, wfp)
            self.log("story not found. adding to list")
        yield None

    def show_ip(self, response):
        print("current ip", response.body)
        yield None
    
