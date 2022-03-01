import re
import copy
import json
import time
import hashlib

import requests

BASE_URL = "https://www.youtube.com/youtubei/v1/browse?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
POST_DATA = {"context": {"client": {"clientName": "WEB", "clientVersion": "2.20220224.07.00"}}}
FIRST_PARAM = '{{"browseId": "{browseId}", "params": "{params}"}}'
CONTINUATION_PARAM = '{{"continuation": "{token}"}}'

class YT_Posts():

    def __init__(self, cookie: str = None) -> None:

        self.headers = {}
        if cookie:
            self.cookie_dict = self.parseCookies(cookie)
            if self.cookie_dict:
                self.build_headers()

    @staticmethod
    def parseCookies(cookie: str) -> dict:
        cookie_keys = ["SID", "HSID", "SSID", "APISID", "SAPISID"]
        parsed_cookies = {}
        for each_cookie_key in cookie_keys:
            result = re.search(f'(;| ){each_cookie_key}=(.*?);', cookie)
            if not result:
                return False
            parsed_cookies.update({each_cookie_key:result.group(2)})
        return parsed_cookies

    @staticmethod
    def hashString(password: str) -> str:
        hash_object = hashlib.sha1(password.encode())
        pbHash = hash_object.hexdigest()
        return pbHash

    def build_headers(self) -> None:
        sapisid = self.cookie_dict['SAPISID']
        origin = "https://www.youtube.com"
        current_time = str(int(time.time()))
        sapisidhash = self.hashString(f"{current_time} {sapisid} {origin}")
        self.headers = {
            "Authorization": f"SAPISIDHASH {current_time}_{sapisidhash}",
            "Cookie": '; '.join('='.join((key,val)) for (key,val) in self.cookie_dict.items()),
            "x-origin": origin
        }

    @staticmethod
    def combineText(text_dict: dict) -> str:
        text = ""
        for each_text in text_dict:
            text += each_text["text"]
        return text

    def cleanUpPostResults(self, post_dict: dict) -> dict:
        result_dict = {
            "postParams": None,
            "postId": None,
            "text": None,
            "images": None,
            "videos": None,
            "polls": None
        }
        
        if "backstagePostThreadRenderer" not in post_dict.keys():
            return False

        post_dict = post_dict["backstagePostThreadRenderer"]["post"]["backstagePostRenderer"]

        result_dict["postId"] = post_dict["postId"]
        result_dict["postParams"] = post_dict["publishedTimeText"]["runs"][0]["navigationEndpoint"]["browseEndpoint"]["params"]

        # Join all texts
        result_dict["text"] = self.combineText(post_dict["contentText"]["runs"])

        # Clean up attachments (polls, single images, image gallery, videos)
        if "backstageAttachment" in post_dict.keys():
            images = []
            
            # Single Image
            if "backstageImageRenderer" in post_dict["backstageAttachment"].keys():
                images.append(post_dict["backstageAttachment"]["backstageImageRenderer"]["image"]["thumbnails"][-1])

            # Multi Image
            if "postMultiImageRenderer" in post_dict["backstageAttachment"].keys():
                for each_image in post_dict["backstageAttachment"]["postMultiImageRenderer"]['images']:
                    images.append(each_image["backstageImageRenderer"]["image"]["thumbnails"][-1])

            result_dict["images"] = images

            # Videos
            videos = {}
            if "videoRenderer" in post_dict["backstageAttachment"].keys():
                videos["text"] = self.combineText(post_dict["backstageAttachment"]["videoRenderer"]["title"]["runs"])
                videos["videoId"] = post_dict["backstageAttachment"]["videoRenderer"]["videoId"]
            result_dict["videos"] = videos

            # Polls
            polls = {
                "choices": [],
                "totalVotes": 0
            }
            
            if "pollRenderer" in post_dict["backstageAttachment"].keys():
                choices = []
                for each_choice in post_dict["backstageAttachment"]["pollRenderer"]["choices"]:
                    choice_dict = {}
                    choice_dict["text"] = self.combineText(each_choice["text"]["runs"])
                    # Field doesn't exist if you haven't voted
                    if "numVotes" in each_choice:
                        choice_dict["numVotes"] = each_choice["numVotes"]
                        choice_dict["votePercentage"] = each_choice["votePercentage"]["simpleText"]
                    else:
                        choice_dict["numVotes"] = 0
                        choice_dict["votePercentage"] = each_choice["votePercentageIfNotSelected"]["simpleText"] #Assume false if haven't voted
                    choices.append(choice_dict)
                polls["choices"] = choices
                polls["totalVotes"] = post_dict["backstageAttachment"]["pollRenderer"]["totalVotes"]["simpleText"]
            result_dict["polls"] = polls

        return result_dict
        
    def cleanUpCommentResults(self, comment_dict: dict, reply: bool) -> dict:
        result_dict = {
            "commentId": None,
            "authorName": None,
            "commentText": None,
            "emojis": None,
            "replyToken": None,
            "replyCount": None,
        }   
        
        if not reply and "commentThreadRenderer" not in comment_dict.keys():
            return False

        if not reply and "replies" in comment_dict["commentThreadRenderer"].keys():
            result_dict['replyToken'] = comment_dict["commentThreadRenderer"]["replies"]["commentRepliesRenderer"]["contents"][0]['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token']
            result_dict['replyCount'] = comment_dict["commentThreadRenderer"]["comment"]["commentRenderer"]["replyCount"]

        if not reply:
            comment_dict = comment_dict["commentThreadRenderer"]["comment"]["commentRenderer"]
        else:
            comment_dict = comment_dict["commentRenderer"]

        result_dict["commentId"] = comment_dict["commentId"]

        result_dict["authorName"] = comment_dict["authorText"]["simpleText"]
        result_dict["commentText"] = self.combineText(comment_dict["contentText"]["runs"])

        emojis = []
        for text in comment_dict["contentText"]["runs"]:
            if "emoji" in text.keys():
                emojis.append({
                    "emojiName": text["text"],
                    "emojiUrl": text["emoji"]["image"]["thumbnails"][-1]["url"]
                })

        result_dict["emojis"] = emojis
        return result_dict

    def fetchPosts(self, channel_id: str, limit: int = 10) -> dict:

        post_data = copy.deepcopy(POST_DATA)
        post_data.update(json.loads(FIRST_PARAM.format(browseId=channel_id, params="Egljb21tdW5pdHk%3D")))
        r = requests.post(BASE_URL, headers=self.headers, data=json.dumps(post_data)).json()
        community_posts = r['contents']['twoColumnBrowseResultsRenderer']['tabs'][3]['tabRenderer']['content']['sectionListRenderer']['contents'][0]["itemSectionRenderer"]["contents"]

        if limit > 10:
            for _ in range(10, limit, 10):
                if 'continuationItemRenderer' in community_posts[-1].keys():
                    continuation = community_posts.pop()
                    post_data = copy.deepcopy(POST_DATA)
                    post_data.update(json.loads(CONTINUATION_PARAM.format(token=continuation['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token'])))
                    r = requests.post(BASE_URL, headers=self.headers, data=json.dumps(post_data)).json()
                    community_posts.extend(r['onResponseReceivedEndpoints'][0]['appendContinuationItemsAction']['continuationItems'])

        if 'continuationItemRenderer' in community_posts[-1].keys():
            community_posts.pop()

        community_posts = community_posts[:limit]
        cleaned_posts = []

        for each_post in community_posts:
            cleaned_post = self.cleanUpPostResults(each_post)
            if cleaned_post:
                cleaned_posts.append(cleaned_post)
        return cleaned_posts

    def fetchPost(self, channel_id:str, post_id: str) -> dict:

        post_data = copy.deepcopy(POST_DATA)
        post_data.update(json.loads(FIRST_PARAM.format(browseId=channel_id, params=post_id)))
        r = requests.post(BASE_URL, headers=self.headers, data=json.dumps(post_data)).json()
        result = r['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents']
        community_post = result[0]["itemSectionRenderer"]["contents"][0]
        cleaned_post = self.cleanUpPostResults(community_post)
        comment_continuation = result[1]["itemSectionRenderer"]["contents"][0]['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token']
        
        return {
            "post": cleaned_post,
            "commentToken": comment_continuation,
        }

    def fetchComment(self, token: str, limit: int = 20, reply: bool = False) -> dict:
        post_data = copy.deepcopy(POST_DATA)
        post_data.update(json.loads(CONTINUATION_PARAM.format(token=token)))
        r = requests.post(BASE_URL, headers=self.headers, data=json.dumps(post_data)).json()
        if not reply:
            commentCount = r['onResponseReceivedEndpoints'][0]['reloadContinuationItemsCommand']['continuationItems'][0]["commentsHeaderRenderer"]["commentsCount"]["runs"][0]["text"]
            comments = r['onResponseReceivedEndpoints'][1]['reloadContinuationItemsCommand']['continuationItems']
        else:
            commentCount = 0
            comments = r['onResponseReceivedEndpoints'][0]['appendContinuationItemsAction']['continuationItems']
        
        if limit > 20:
            for _ in range(20, limit, 20):
                if 'continuationItemRenderer' in comments[-1].keys():
                    continuation = comments.pop()
                    post_data = copy.deepcopy(POST_DATA)
                    post_data.update(json.loads(CONTINUATION_PARAM.format(token=continuation['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token'])))
                    r = requests.post(BASE_URL, headers=self.headers, data=json.dumps(post_data)).json()
                    comments.extend(r['onResponseReceivedEndpoints'][0]['appendContinuationItemsAction']['continuationItems'])

        if 'continuationItemRenderer' in comments[-1].keys():
            comments.pop()

        comments = comments[:limit]
        cleaned_comments = []
        for each_comment in comments:
            cleaned_comment = self.cleanUpCommentResults(each_comment, reply)
            if cleaned_comment:
                cleaned_comments.append(cleaned_comment)
        
        if reply:
            print(cleaned_comments)
            print(len(comments))
        
        return {
            "commentCount": commentCount,
            "comments" : cleaned_comments
        }