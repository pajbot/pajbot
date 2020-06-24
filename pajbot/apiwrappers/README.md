# apiwrappers

This module contains wrappers around APIs pajbot uses.

Below are some basic guidelines for implementing new API wrappers:

- Each API should live in its own file. If a provider (e.g Twitch) has multiple API resources (e.g. Kraken, TMI, Helix, Badges, etc.) then each should be in its own file.
- Each API Wrapper should extend from `BaseAPI`: It provides a simple mechanism for calling endpoints on a base URL.
- Each API wrapper should only service a single API at a single endpoint. The endpoint is typically set inside `__init__`, with the call to the superclass.

  In `__init__`, call `super().__init__(base_url="https://api.company.com/v1/")` - notice the keyword-argument (`base_url=`) and the slash at the end of the URL.

## Basic usage

To actually call the API, use `self.get`, `self.post`, `self.put`, etc. (Note that some of the HTTP verbs might be missing in the Base API, add them should you need them).

The first parameter of `self.<method>` is the **endpoint** to call - This is either a string (when the endpoint is constant) or a list of path segments the Base API will safely concatenate for you:

```python
# These two do the same thing!
self.get("/hello/world")
self.get(["hello", "world"])
```

The real value of the list-parameter is of course variable parameters (which would then automatically be URL-encoded), e.g.:

```python
# GET /users/:username
self.get(["users", username])
```

The other parameters to these methods are:

- `params` can be set to a dict of query string parameters,
- `headers` can be set to a dict of headers to send,
- In `post()` and `put()`, `json` can be set to a dict/list/scalar to serialize and send as the request body,
- and all other `**kwargs` are passed on to the [requests](https://requests.kennethreitz.org/en/master/) module.

## Defaults

You can set default headers, and other "defaults" using `self.session` after calling `super().__init__()`:

```python
class SomeProviderAPI(BaseAPI):
    def __init__(self, client_id):
        super().__init__(base_url="https://some-provider.com/api/v1/")

        # Send "Authorization: Client-ID <client_id>" on all requests by default
        self.session.headers["Authorization"]  = f"Client-ID {client_id}"
```

`self.session` is just a plain `Session` from the [requests](https://requests.kennethreitz.org/en/master/) module.

## Data models and scalars

API Wrapper methods should not return the format the API returns, in raw. E.g. this would not be a very useful API Wrapper:

```python
class SomeProviderAPI(BaseAPI):
    def __init__(self):
        super().__init__(base_url="https://some-provider.com/api/v1/")

    def get_user(self, username):
        return self.get(["users", username])
```

The user of the API would call `get_user` - and the API wrapper would just return the parsed JSON the API returned. This kind of API wrapper provides almost no useful extra layer of abstraction over the base API, except for maybe hiding the endpoint that has to be called.

A more useful approach is to make methods that either return complete data class models, or methods that return scalars (e.g. strings, numbers, etc.):

```python
import isodate

class SomeProviderUser:
    def __init__(self, username, created_at, email_address, phone_number):
        self.username = username
        self.created_at = created_at
        self.email_address = email_address
        self.phone_number = phone_number

class SomeProviderAPI(BaseAPI):
    def __init__(self):
        super().__init__(base_url="https://some-provider.com/api/v1/")

    def get_user(self, username):
        response = self.get(["users", username])

        return SomeProviderUser(
            username=response["username"],
            created_at=isodate.parse_duration(response["created_at"]),
            email_address=response["email_address"],
            phone_number=response["phone_number"]
        )
```

`get_user()` now returns a user model. This is not only more pleasant to use (compare `user["username"]` to `user.username`), but also contains further-parsed data, e.g. in the example above a string is being parsed into a `datetime.datetime` instance.

To return to the original point: Either return an instance of a data model (not a dict or json), **or** return only scalars. Observe for example:

```python
class SomeProviderAPI(BaseAPI):
    def __init__(self):
        super().__init__(base_url="https://some-provider.com/api/v1/")

    def get_user_phone_number(self, username):
        response = self.get(["users", username])

        return response["phone_number"]
```

In this case, we don't need to define a data model first, since we'd only be returning a string. However, if you were to expand the example above with the full data model, you would write:

```python
# ... snip ...
def get_user_phone_number(self, username):
      return self.get_user(username).email_address
```

(Although one could argue that kind of method is pretty pointless)

## Processing data further with utility methods

If you find yourself doing the same thing often, you can define a utility directly inside the API Wrapper (as long as it doesnt diverge from the intent of an _API wrapper_ too far), e.g.:

```python
def get_older_user(self, first_username, second_username):
    first_user = self.get_user(first_username)
    second_user = self.get_user(second_username)

    if first_user.created_at > second_user.created_at:
        return first_user
    else:
        return second_user
```

## Adding caching

If you want to add caching, you need a two (or three)-step indirection like this:

```
user code <=> get_older_user <=> get_user (<=> self.cache.cache_fetch_fn )<=> _fetch_user
```

- `user code` is the place calling/using the API wrapper
- `get_older_user` is an example for a method that further extracts/processes data based upon data from an endpoint.
- `get_user` is the public API method user code would call to get a plain model.
- `self.cache.cache_fetch_fn` is called inside `get_user`, with a reference to `self._fetch_user`
- `_fetch_user` is the method that makes the API request, and parses the response into an instance of the model.

```python
from pajbot.utils import datetime_from_utc_milliseconds

import isodate

class SomeProviderUser:
    def __init__(self, username, created_at, email_address, phone_number):
        self.username = username
        self.created_at = created_at
        self.email_address = email_address
        self.phone_number = phone_number

    # jsonify() creates a value that `json.dumps()` can accept, e.g. a dict
    def jsonify(self):
        return {
            "username": self.username,
            "created_at": self.created_at.timestamp() * 1000,
            "email_address": self.email_address,
            "phone_number": self.phone_number
        }

    # from_json() recovers an instance using the JSON that jsonify() produced.
    # This method is NOT meant to parse the JSON response from the original API!
    # That logic is part of the API wrapper, and should live inside _fetch_xxx or get_xxx functions.
    @staticmethod
    def from_json(json_data):
        return SomeProviderUser(
            username=json_data["username"],
            created_at=datetime_from_utc_milliseconds(json_data["created_at"]),
            email_address=json_data["email_address"],
            phone_number=json_data["phone_number"]
        )

class SomeProviderAPI(BaseAPI):
    def __init__(self, redis):
        super().__init__(base_url="https://some-provider.com/api/v1/", redis=redis)

    def _fetch_user(self, username):
        response = self.get(["users", username])

        return SomeProviderUser(
            username=response["username"],
            created_at=isodate.parse_duration(response["created_at"]),
            email_address=response["email_address"],
            phone_number=response["phone_number"]
        )

    def get_user(self, username):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:some-provider:user:{username}",
            fetch_fn=lambda: self._fetch_user(username)
            # Extra optional options:
            # serializer=JsonSerializer() -
            #   Defines how the value is serialized/deserialized,
            #   See the top of response_cache.py for available implementations/how they work,
            # expiry=<number> - Sets the cache expiration in seconds (defaults to 120 seconds)
            # expiry=lambda result: <lambda that returns an integer> -
            #   Sets the cache expiration in seconds,
            #   dynamically based upon what result the fetch function yielded
            # force_fetch=<bool> - If True, then the cache lookup is skipped,
            #   and a fetch always occurs. The result will be saved to the cache nevertheless.
        )

    def get_older_user(self, first_username, second_username):
        first_user = self.get_user(first_username)
        second_user = self.get_user(second_username)

        if first_user.created_at > second_user.created_at:
            return first_user
        else:
            return second_user
```

- We added `jsonify` and `from_json` methods to our user model, to allow it to be serialized and deserialized.
- The `redis` parameter has been added to the constructor, and is passed onto the super constructor, so we can use `self.cache`.

  If the super constructor is given a `redis` instance, it will set `self.cache` to an instance of `APIResponseCache`. `APIResponseCache` defines two methods: `cache_fetch_fn` and `cache_bulk_fetch_fn`.

- The `get_user` method now calls the cache, which we instruct to call `_fetch_user` on cache miss.
- `get_older_user` remains unchanged.

## Comments

Please add comments where the response format of the API is not immediately obvious:

For example, you can add a big comment with an entire example response:

```python
def get_something(self, some_input, another_input):
    response = self.post(...)

    # response =
    # {
    #   "access_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"
    #   "expires_in": 14310,
    #   "refresh_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    #   "scope": [
    #     "user_read"
    #   ],
    #   "token_type": "bearer"
    # }

    return ...
```

Or something shorter, like this (Example from the Google Safe Browsing API wrapper):

```python
def is_url_bad(self, url):
    resp = self.post("/threatMatches:find", json=...)

    # good response: {} or {"matches":[]}
    # bad response: {"matches":[{ ... }]}

    return len(resp.get("matches", [])) > 0
```

## Errors, and None return values

In the above examples, we never handled the case where the user we were looking for does not exist. There are two ways you can deal with this in new API wrappers:

- **Return `None`** for methods that strictly _get_ data and where the absence of data is not generally an error case, but can happen normally (like for example `get_user`) - or e.g. in the case of the BTTV API wrapper - when a channel has no emotes
- **Raise an exception** in all other cases, and in cases where the non-existance of data either means the method cannot continue normally.

Take for example a method that seeks to fetch the currently playing song on Dubtrack - Say we first query the API for the current song, and then we query the API again in another call for the song's title, author, youtube link, etc. The second API call looks up the song using the internal ID the song is given by Dubtrack (which we got in the first API call's response) - in this case, getting a 404 Not Found error in the second API call would be an error condition. Getting the 404 Not Found error in the first stage (e.g. nothing currently playing), then the correct thing would be to return `None`.

## Summary

So in total, there are three main ways of adding structure to the API wrapper:

- Parsing raw responses into models instead of directly reading scalars from the response
- Caching via `get_xxx` and `_fetch_xxx`
- Higher-level functions that depend on other `get_xxx` methods

Apply these abstraction layers as needed, where they are required to get a certain API wrapper interface (e.g. if you want to make a method to return data models), or when cache is needed you add the cache indirection etc.

For example, if all you wanted was to get user's emails, and nothing else, you could write (same example as above) - And this would be a good API wrapper all things considered:

```python
class SomeProviderAPI(BaseAPI):
    def __init__(self):
        super().__init__(base_url="https://some-provider.com/api/v1/")

    def get_user_phone_number(self, username):
        response = self.get(["users", username])

        return response["phone_number"]
```

Another example: You can of course also pass scalars through `cache_fetch_fn` - If you don't need a model, but you want a cache layer.
