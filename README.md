# youtube-community-posts
Fetch youtube community posts contents and comments

## Methods

- `fetchPosts(channel_id, limit=10)`

Fetches all community posts from a channel specified.

`channel_id` -> ID of the youtube channel to fetch from.

`limit` -> The number of posts to fetch. Default is 10.

----
- `fetchPost(channel_id, postParam)`

Fetch a community post data with its postParam obtained from `fetchPosts`.

`channel_id` -> ID of the youtube channel to fetch from.

`postParam` -> postParam obtained from `fetchPosts`.

----
- `fetchComment(commentToken, limit=20, reply=False)`

Fetch a comment from `fetchPost` comments results.

`commentToken` -> `commentToken` from `fetchPosts`.

`limit` -> The number of comments to fetch. Default is 20.

`reply` -> `True` if the supplied comment token is token from single `fetchComment` result.

----

### Fetching result as authenticated account

1. Open incognito browser and open developer console.
2. Browse to network tab and enable Preserve log.
3. Type in set_registration in the network search bar.
4. Go to https://www.youtube.com/ and login as usual.
5. Then select the 2nd result and then copy the whole cookie from the request headers.
6. Pass the cookie when creating the object. 
Example: 
```
from yTposts import YT_Posts
yt = YT_Posts(cookie_string)
```
----

### Example Usage
```
from yTposts import YT_Posts

channel_id = "UC47rNmkDcNgbOcM-2BwzJTQ"
yt = YT_Posts()
community_posts = yt.fetchPosts(channel_id, limit=2)
single_community_post = yt.fetchPost(channel_id, community_posts[0]["postParams"])
comments = yt.fetchComment(single_community_post["commentToken"], limit=999)
replies_to_comment = yt.fetchComment(comments["comments"][0]["replyToken"], reply=True)
```
