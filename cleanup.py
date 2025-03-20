import requests
from dotenv import load_dotenv
import os
import re

load_dotenv()
APIKEY = os.getenv("APIKEY")
NSHOST = os.getenv("NSHOST")
RESELLER = os.getenv("RESELLER")

base_url = f"https://{NSHOST}/ns-api/v2/"


def ask_yes_no(prompt):
    """
    Prompt the user for a yes/no answer.
    Returns True for yes, False for no.
    If the user enters nothing, defaults to no.
    """
    while True:
        # The prompt indicates that the default is No by using [y/N]
        answer = input(f"{prompt} [y/N]: ").strip().lower()

        if answer == "":
            # Default to "no" if no input is provided
            return False
        elif answer in ("y", "yes"):
            return True
        elif answer in ("n", "no"):
            return False
        else:
            print(f"{prompt} [y/N]: ")


def unique_by_keys(dict_list, keys):
    """
    Returns a list of dictionaries from dict_list that are unique with respect to the specified keys.
    Also excludes dictionaries that contain any value with characters other than underscore, hyphen, period, letters, or numbers.
    The first occurrence is kept.
    """
    allowed_pattern = re.compile(r"^[A-Za-z0-9_.-]+$")
    seen = set()
    unique_list = []

    for d in dict_list:
        valid = True
        for k in keys:
            value = d.get(k)
            if isinstance(value, str) and not allowed_pattern.match(value):
                valid = False
                break
        if not valid:
            continue

        key_tuple = tuple((k, d.get(k)) for k in keys)
        if key_tuple not in seen:
            seen.add(key_tuple)
            unique_list.append(d)
    return unique_list


def check_if_domain_exists(domain):
    func_url = f"{base_url}domains/{domain}/count"

    headers = {"accept": "application/json", "authorization": f"Bearer {APIKEY}"}

    response = requests.get(func_url, headers=headers)
    data = response.json()
    answer = bool(data["total"])
    return answer


def check_if_user_exists(user, domain):
    func_url = f"{base_url}domains/{domain}/users/{user}/count"

    headers = {"accept": "application/json", "authorization": f"Bearer {APIKEY}"}

    response = requests.get(func_url, headers=headers)
    data = response.json()
    print(data)
    answer = bool(data["total"])
    return answer


def build_domain(domain):
    func_url = f"{base_url}domains"

    payload = {
        "synchronous": "no",
        "language-token": "en_US",
        "domain": domain,
        "reseller": RESELLER,
        "description": "CLEANUP",
        "domain-type": "Standard",
        "area-code": 100,
        "caller-id-number": 1234567890,
        "caller-id-number-emergency": 1234567890,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {APIKEY}",
    }

    requests.post(func_url, json=payload, headers=headers)
    return


def delete_domain(domain):
    func_url = f"{base_url}domains/{domain}"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {APIKEY}",
    }

    requests.delete(func_url, headers=headers)
    return


def build_user(user, domain):
    func_url = f"{base_url}domains/{domain}/users"

    payload = {
        "user": user,
        "name-first-name": "CLEANUP",
        "name-last-name": "CLEANUP",
        "email-address": f"{user}@CLEANUP.com",
        "user-scope": "No Portal",
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {APIKEY}",
    }

    requests.post(func_url, json=payload, headers=headers)
    return


def delete_user(user, domain):
    func_url = f"{base_url}domains/{domain}/users/{user}"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {APIKEY}",
    }

    requests.delete(func_url, headers=headers)
    return


def build_callqueue(queue, domain):
    func_url = f"{base_url}domains/{domain}/callqueues"

    payload = {
        "synchronous": "no",
        "callqueue": queue,
        "callqueue-dispatch-type": "Ring All",
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {APIKEY}",
    }

    requests.post(func_url, json=payload, headers=headers)
    return


def delete_callqueue(queue, domain):
    func_url = f"{base_url}domains/{domain}/callqueues/{queue}"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {APIKEY}",
    }

    requests.delete(func_url, headers=headers)
    return


def delete_queue_agents(agent_id, queue, domain):
    func_url = f"{base_url}domains/{domain}/callqueues/{queue}/agents/{agent_id}"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {APIKEY}",
    }

    requests.delete(func_url, headers=headers)
    return


def cleanup_callqueue_agents(orphaned_agents):
    """
    takes in a list of dictionaries in the form of:
    {'device_aor': '<agent ID>', 'huntgroup_name': '<callqueue>', 'huntgroup_domain': '<domain>'}
    """
    missing_queues = unique_by_keys(
        orphaned_agents, ["huntgroup_name", "huntgroup_domain"]
    )
    print(f"There are {len(missing_queues)} queues with orphaned agents.")
    for queue in missing_queues:
        queue_name = queue.get("huntgroup_name")
        queue_domain = queue.get("huntgroup_domain")
        orphaned_agent_ids = [
            d["device_aor"]
            for d in orphaned_agents
            if d["huntgroup_name"] == queue["huntgroup_name"]
            and d["huntgroup_domain"] == queue["huntgroup_domain"]
        ]
        verdict = ask_yes_no(
            f"Cleanup {queue_name}@{queue_domain} for {len(orphaned_agent_ids)} agents"
        )

        if not verdict:
            print("you chose NOT to clean")
            continue
        else:
            print("you chose to cleanup")

        domain_existed = check_if_domain_exists(queue_domain)

        if not domain_existed:
            print(f"Building domain: {queue_domain}")
            build_domain(queue_domain)
            user_existed = False
        else:
            user_existed = check_if_user_exists(queue_name, queue_domain)

        if not user_existed:
            print(f"Building User: {queue_name}@{queue_domain}")
            build_user(queue_name, queue_domain)

        print(f"Building queue: {queue_name}@{queue_domain}")
        build_callqueue(queue_name, queue_domain)
        for user in orphaned_agent_ids:
            print(f"Deleting agent: {user} from queue {queue_name}@{queue_domain}")
            delete_queue_agents(user, queue_name, queue_domain)

        # cleanup things that had to be built
        print(f"deleting queue: {queue_name}@{queue_domain}")
        delete_callqueue(queue_name, queue_domain)
        if not domain_existed:
            print(f"Deleting user: {queue_name}")
            delete_user(queue_name, queue_domain)

            print(f"Deleting domain: {queue_domain}")
            delete_domain(queue_domain)
        elif not user_existed:
            print(f"Deleting user: {queue_name}")
            delete_user(queue_name, queue_domain)
