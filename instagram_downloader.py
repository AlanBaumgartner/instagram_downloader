import aiohttp, asyncio, argparse, os

async def download_file(username, url, session, sem, loop=None):
    async with sem:
        async with session.get(url) as resp:
            out = await resp.read()
            filename = url.split('/')[-1]
            path = username + '/' + filename
            if not os.path.exists(username):
                os.makedirs(username)
            with open(path, 'wb') as f:
                f.write(out)

async def getJSON(url, session):
    async with session.get(url) as resp:
        data = await resp.json()
        return data

async def main(usernames, conns=50, loop=None):
    async with aiohttp.ClientSession(loop=loop) as session:
        for username in usernames:
            sem = asyncio.BoundedSemaphore(conns)
            url = 'http://instagram.com/' + username + '/media/?max_id='
            urls = []
            max_id = ''
            moreDataToFetch = True
            while(moreDataToFetch):
                nextUrl = url + max_id
                jsonData = await getJSON(nextUrl, session)
                moreDataToFetch = jsonData['more_available']
                for item in jsonData['items']:
                    imgUrl = None
                    max_id = item['id']
                    if item['type'] == 'image':
                        imgUrl = item['images']['standard_resolution']['url']
                    elif item['type'] == 'video':
                        imgUrl = item['videos']['standard_resolution']['url']
                    urls.append(imgUrl)

            tasks = [download_file(username, url, session, sem, loop=loop) for url in urls]
            await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", dest='username', help="Instagram username to download photos from",
                        action="store", nargs="+")
    args = parser.parse_args()
    usernames = args.username

    loop = asyncio.get_event_loop() 
    loop.run_until_complete(main(usernames))
