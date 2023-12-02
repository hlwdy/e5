import json
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor
import os
import signal
from deta import Deta

class GracefulKiller:
    """https://stackoverflow.com/questions/18499497/how-to-process-sigterm-signal-gracefully
    """
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        # https://stackoverflow.com/questions/33242630/how-to-handle-os-system-sigkill-signal-inside-python
        # signal.signal(signal.SIGKILL, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True

MIN_INVOKE_TIMES = 2
MAX_INVOKE_TIMES = 4
EXECUTOR_POOL_SIZE = 7
EXECUTOR_KILLER = GracefulKiller()

token_db_key=os.environ['dbkey']
db_key=os.environ['dbtoken']
def get_new_token():
    return Deta(db_key).Base('pan').fetch({'key':token_db_key}).items[0]['token']
def put_new_token(t):
    return Deta(db_key).Base('pan').put({'token':t},token_db_key)

def get_access_token(app):
    try:
        return requests.post(
            'https://login.microsoftonline.com/common/oauth2/v2.0/token'.replace('login.microsoftonline.com',os.environ['lgproxy']),
            data={
                'grant_type': 'refresh_token',
                'refresh_token': app['refresh_token'],
                'client_id': app['client_id'],
                'client_secret': app['client_secret'],
                'redirect_uri': app['redirect_uri']
            }
        ).json()
    except Exception as e:
        return {}


def invoke_api():
    app={'client_id':os.environ['id'],'client_secret':os.environ['secret'],'redirect_uri':'http://localhost:8080','refresh_token':get_new_token()}
    tokens = get_access_token(app)
    #print(tokens)
    print('token ok')
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    if len(access_token) < 50 or len(refresh_token) < 50:
         return f'✘ 账号api调用失败.'

    put_new_token(refresh_token)

    apis = [
        'https://graph.microsoft.com/v1.0/sites/root',
        'https://graph.microsoft.com/v1.0/sites/root/sites',
        'https://graph.microsoft.com/v1.0/sites/root/drives',
        'https://graph.microsoft.com/v1.0/sites/root/columns',
        'https://graph.microsoft.com/v1.0/me/',
        'https://graph.microsoft.com/v1.0/me/people',
        'https://graph.microsoft.com/v1.0/me/contacts',
        'https://graph.microsoft.com/v1.0/me/calendars',
        'https://graph.microsoft.com/v1.0/me/drive',
        'https://graph.microsoft.com/v1.0/me/drive/root',
        'https://graph.microsoft.com/v1.0/me/drive/root/children',
        'https://graph.microsoft.com/v1.0/me/drive/recent',
        'https://graph.microsoft.com/v1.0/me/drive/sharedWithMe',
        'https://graph.microsoft.com/v1.0/me/onenote/pages',
        'https://graph.microsoft.com/v1.0/me/onenote/sections',
        'https://graph.microsoft.com/v1.0/me/onenote/notebooks',
        'https://graph.microsoft.com/v1.0/me/outlook/masterCategories',
        'https://graph.microsoft.com/v1.0/me/mailFolders',
        'https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages/delta',
        'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messageRules',
        'https://graph.microsoft.com/v1.0/me/messages',
        "https://graph.microsoft.com/v1.0/me/messages?$filter=importance eq 'high'",
        'https://graph.microsoft.com/v1.0/me/messages?$search="pdf"',
        'https://graph.microsoft.com/beta/me/messages?$select=internetMessageHeaders&$top',
    ]
    headers = {'Authorization': f'Bearer {access_token}'}

    def single_period(period):
        if EXECUTOR_KILLER.kill_now:
            return ''

        result = '======================================================================================\n'
        curapi=random.sample(apis,random.randint(4,8))
        random.shuffle(curapi)

        proxy_=os.environ['proxy']

        for api in curapi:
            try:
                r=requests.get(api.replace('graph.microsoft.com',proxy_), headers=headers)
                print(api+' | '+str(r.status_code))
                if r.status_code == 200:
                    print( '{:>6s} | {:<50s}\n'.format(
                        f'周期: {period}',
                        f'成功: {api}'
                    ))
                    
            except Exception:
                # time.sleep(random.random()*1)
                pass

            if EXECUTOR_KILLER.kill_now:
                return result

        return result

    periods = random.randint(MIN_INVOKE_TIMES, MAX_INVOKE_TIMES)

    futures, pool = [],  ThreadPoolExecutor(EXECUTOR_POOL_SIZE)
    for period in range(1, periods):
        futures.append(pool.submit(single_period, period))

    result = ''
    for future in futures:
        result += future.result()

    pool.shutdown()


    return f'{result}✔ 调用成功.'


if __name__ == '__main__':
    print(invoke_api())
