import os

def proxies(username, password, endpoint, port):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxies",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
            mode: "fixed_servers",
            rules: {
              singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
              },
              bypassList: ["localhost"]
            }
          };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (endpoint, port, username, password)

    directory_name = os.path.join(os.getcwd(), "utilitarios", "proxy")
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    manifest_path = os.path.join(directory_name, "manifest.json")
    background_path = os.path.join(directory_name, "background.js")

    with open(manifest_path, 'w') as manifest_file:
        manifest_file.write(manifest_json)

    with open(background_path, 'w') as background_file:
        background_file.write(background_js)

if __name__ == '__main__':
    username = "u5d07236857af05c7-zone-custom"
    password = "u5d07236857af05c7"
    endpoint = "43.152.113.55"
    port = '2334'

    proxies(username, password, endpoint, port)
    print("Proxies instalados correctamente.")