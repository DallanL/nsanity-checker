import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
from cleanup import cleanup_callqueue_agents


def get_db_connection():
    """
    Loads database credentials from the .env file and establishes a connection
    to the SiPbxDomain database.
    """
    load_dotenv()  # Load environment variables from .env
    host = os.getenv("NSHOST")
    user = os.getenv("DBUSER")
    password = os.getenv("DBPASS")
    database = "SiPbxDomain"

    try:
        connection = mysql.connector.connect(
            host=host, user=user, password=password, database=database
        )
        if connection.is_connected():
            print("Connected to MariaDB database")
            return connection
    except Error as e:
        print(f"Error while connecting to database: {e}")
    return None


def check_dial_rules_have_dialplan(connection):
    """
    Checks that every entry in the dialplan_config table has a corresponding
    entry in the dialplans table based on the 'dialplan' field.
    Prints out orphan entries where the parent dialplan is missing.
    """
    cursor = connection.cursor(dictionary=True)

    # Using a LEFT JOIN to find orphan entries in dialplan_config.
    query = """
        SELECT 
            c.dialplan,
            c.matchrule, 
            c.responder, 
            c.domain, 
            c.plan_description 
        FROM dialplan_config c
        LEFT JOIN dialplans d ON c.dialplan = d.dialplan
        WHERE d.dialplan IS NULL;
    """
    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print(
                "Orphan entries found in dialplan_config (no matching dialplan in dialplans):"
            )
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")

        else:
            print(
                "All entries in dialplan_config have corresponding dialplan entries in dialplans."
            )
    except Error as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def check_dialplans_have_domain(connection):
    """
    Checks that every entry in the dialplans table has a corresponding entry
    in the domains_config table based on the 'domain' field.
    Orphan entries are those where the parent domain is missing.
    The check ignores entries where the dialplan is in a predefined ignore list.
    All columns from the dialplans table are selected.
    Also prints the number of orphan entries found at the bottom.
    """
    cursor = connection.cursor(dictionary=True)

    # Define the list of dialplan entries to ignore
    ignore_list = [
        "To Connection",
        "Default",
        "Inbound DID",
        "DID Table",
        "AA-Basic",
        "Restricted",
        "Starcodes",
        "From Load Balanced Peer",
        "Asserted_Defaults",
        "Lower_Case_Defaults",
        "To Connection - Forward",
        "fwd-check",
        "Default STIR SHAKEN",
        "Cloud PBX Features",
        "Forward Blocking",
        "Default_New",
    ]

    # Create a string with comma-separated quoted ignore values
    ignore_values = ", ".join(f"'{item}'" for item in ignore_list)

    query = f"""
        SELECT
            d.*
        FROM dialplans d
        LEFT JOIN domains_config dc ON d.domain = dc.domain
        WHERE dc.domain IS NULL
          AND d.dialplan NOT IN ({ignore_values});
    """

    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print("Orphan entries in dialplans (no matching domain in domains_config):")
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")
        else:
            print(
                "All entries in dialplans have corresponding domain entries in domains_config."
            )
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def check_domains_have_reseller(connection):
    """
    Checks that every entry in domains_config has a corresponding territory in the territories table.
    Specifically, it verifies that the 'territory' value in domains_config exists in the territories table.
    Only the columns 'domain', 'territory', and 'description' are selected.
    Orphan entries (with no matching territory) are printed followed by the total count.
    """
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT 
            dc.domain, 
            dc.territory, 
            dc.description
        FROM domains_config dc
        LEFT JOIN territories t ON dc.territory = t.territory
        WHERE t.territory IS NULL;
    """

    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print(
                "Orphan entries in domains_config (no matching territory in territories):"
            )
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")
        else:
            print(
                "All entries in domains_config have a corresponding territory in territories."
            )
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def check_huntgroup_agents_have_huntgroup(connection):
    """
    Checks that every entry in the huntgroup_entry_config table has a corresponding entry
    in the huntgroup_config table by comparing the 'huntgroup_name' and 'huntgroup_domain' columns.
    Only the columns 'device_aor', 'huntgroup_name', and 'huntgroup_domain' are selected from huntgroup_entry_config.
    Orphan entries (where no matching huntgroup exists in huntgroup_config) are printed followed by the total count.
    """
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT 
            hec.device_aor, 
            hec.huntgroup_name, 
            hec.huntgroup_domain
        FROM huntgroup_entry_config hec
        LEFT JOIN huntgroup_config hc 
            ON hec.huntgroup_name = hc.huntgroup_name 
           AND hec.huntgroup_domain = hc.huntgroup_domain
        WHERE hc.huntgroup_name IS NULL;
    """

    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print(
                "Orphan entries in huntgroup_entry_config (no matching huntgroup in huntgroup_config):"
            )
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")
            # only run cleanup if the APIKEY env is set
            if os.getenv("APIKEY"):
                cleanup_callqueue_agents(missing_entries)
        else:
            print(
                "All entries in huntgroup_entry_config have a corresponding huntgroup in huntgroup_config."
            )
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def check_huntgroups_have_callqueues(connection):
    """
    Checks that every entry in huntgroup_config has a corresponding call queue entry
    in callqueue_config by comparing 'huntgroup_name' and 'huntgroup_domain' from huntgroup_config
    with 'queue_name' and 'domain' in callqueue_config.
    Only the columns 'huntgroup_name' and 'huntgroup_domain' are selected from huntgroup_config.
    Orphan entries (with no matching callqueue) are printed followed by the total count.
    """
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT 
            hc.huntgroup_name,
            hc.huntgroup_domain
        FROM huntgroup_config hc
        LEFT JOIN callqueue_config cc 
            ON hc.huntgroup_name = cc.queue_name 
           AND hc.huntgroup_domain = cc.domain
        WHERE cc.queue_name IS NULL;
    """

    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print(
                "Orphan entries in huntgroup_config (no matching callqueue in callqueue_config):"
            )
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")
        else:
            print(
                "All entries in huntgroup_config have corresponding callqueue entries in callqueue_config."
            )
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def check_callqueues_have_users(connection):
    """
    Checks that every entry in callqueue_config has a corresponding entry in subscriber_config
    by comparing 'queue_name' and 'domain' in callqueue_config with 'aor_user' and 'aor_host' in subscriber_config.
    Only the columns 'queue_name' and 'domain' are selected from callqueue_config.
    Orphan entries (with no matching subscriber entry) are printed followed by the total count.
    """
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            cc.queue_name,
            cc.domain
        FROM callqueue_config cc
        LEFT JOIN subscriber_config sc
            ON cc.queue_name = sc.aor_user
           AND cc.domain = sc.aor_host
        WHERE sc.aor_user IS NULL;
    """

    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print(
                "Orphan entries in callqueue_config (no matching subscriber in subscriber_config):"
            )
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")
        else:
            print(
                "All entries in callqueue_config have corresponding subscribers in subscriber_config."
            )
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def check_users_have_domain(connection):
    """
    Checks that every entry in subscriber_config has a corresponding entry in domains_config
    by comparing 'aor_host' in subscriber_config with 'domain' in domains_config.
    Only the columns 'subscriber_login', 'aor_user', and 'aor_host' are selected from subscriber_config.
    Orphan entries (with no matching domain) are printed followed by the total count.
    """
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            sc.subscriber_login,
            sc.aor_user,
            sc.aor_host
        FROM subscriber_config sc
        LEFT JOIN domains_config dc ON sc.aor_host = dc.domain
        WHERE dc.domain IS NULL;
    """

    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print(
                "Orphan entries in subscriber_config (no matching domain in domains_config):"
            )
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")
        else:
            print(
                "All entries in subscriber_config have corresponding domains in domains_config."
            )
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def check_devices_have_users(connection):
    """
    Checks that every entry in registrar_config (representing devices) has a corresponding
    user in subscriber_config by comparing 'aor_user' and 'aor_host' from registrar_config
    with 'subscriber_name' and 'subscriber_domain' in subscriber_config.
    Excludes entries where aor_host is "*" (as these are not applicable).
    Only the columns 'aor_user' and 'aor_host' from registrar_config are selected.
    Orphan entries (with no matching subscriber) are printed followed by the total count.
    """
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            r.aor,
            r.subscriber_name,
            r.subscriber_domain
        FROM registrar_config r
        LEFT JOIN subscriber_config s
            ON r.subscriber_name = s.aor_user
           AND r.subscriber_domain = s.aor_host
        WHERE r.subscriber_domain <> '*'
          AND s.aor_user IS NULL;
    """

    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print(
                "Orphan entries in registrar_config (no matching subscriber in subscriber_config):"
            )
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")
        else:
            print(
                "All entries in registrar_config (with aor_host not '*') have corresponding subscribers in subscriber_config."
            )
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def check_timeframes_have_users(connection):
    """
    Checks that every entry in time_frame_selections has a corresponding entry
    in subscriber_config by comparing 'user' and 'domain' in time_frame_selections
    with 'aor_user' and 'aor_host' in subscriber_config.
    Only the columns 'user' and 'domain' from time_frame_selections are selected.
    Orphan entries (with no matching subscriber) are printed followed by the total count.
    """
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            tfs.user,
            tfs.domain,
            tfs.time_frame_name,
            tfs.error_info
        FROM time_frame_selections tfs
        LEFT JOIN subscriber_config sc
            ON tfs.user = sc.aor_user
           AND tfs.domain = sc.aor_host
        WHERE sc.aor_user IS NULL;
    """

    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print(
                "Orphan entries in time_frame_selections (no matching subscriber in subscriber_config):"
            )
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")
        else:
            print(
                "All entries in time_frame_selections have corresponding subscribers in subscriber_config."
            )
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def check_answeringrules_have_users(connection):
    """
    Checks that every entry in feature_config has a corresponding subscriber in subscriber_config
    by comparing 'callee_match' in feature_config with 'aor_user' in subscriber_config.
    Only the columns 'name', 'callee_match', and 'parameters' are selected from feature_config.
    Orphan entries (with no matching subscriber) are printed followed by the total count.
    """
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT 
            fc.name,
            fc.callee_match,
            fc.parameters
        FROM feature_config fc
        LEFT JOIN subscriber_config sc 
            ON fc.callee_match = sc.subscriber_login
        WHERE sc.subscriber_login IS NULL;
    """

    try:
        cursor.execute(query)
        missing_entries = cursor.fetchall()

        if missing_entries:
            print(
                "Orphan entries in feature_config (no matching subscriber in subscriber_config):"
            )
            for entry in missing_entries:
                print(entry)
            print(f"\nTotal number of orphan entries found: {len(missing_entries)}")
        else:
            print(
                "All entries in feature_config have corresponding subscribers in subscriber_config."
            )
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()


def main():
    """
    Main function to establish database connection and run sanity checks.
    """
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to the database. Exiting.")
        return

    # List of sanity checks as (check_name, function) tuples.
    sanity_checks = [
        ("check_dial_rules_have_dialplan", check_dial_rules_have_dialplan),
        ("check_dialplans_have_domain", check_dialplans_have_domain),
        ("check_domains_have_reseller", check_domains_have_reseller),
        (
            "check_huntgroup_agents_have_huntgroup",
            check_huntgroup_agents_have_huntgroup,
        ),
        ("check_huntgroups_have_callqueues", check_huntgroups_have_callqueues),
        ("check_callqueues_have_users", check_callqueues_have_users),
        ("check_users_have_domain", check_users_have_domain),
        ("check_devices_have_users", check_devices_have_users),
        ("check_timeframes_have_users", check_timeframes_have_users),
        ("check_answeringrules_have_users", check_answeringrules_have_users),
    ]

    # Print the menu.
    print("Select a sanity check to run:")
    print(" 0: Run all checks")
    for index, (name, _) in enumerate(sanity_checks, start=1):
        print(f" {index}: {name}")

    try:
        choice = int(input("Enter your choice: "))
    except ValueError:
        print("Invalid input. Please enter a number.")
        connection.close()
        return

    if choice == 0:
        # Run all sanity checks.
        for name, check_func in sanity_checks:
            print(f"\nRunning {name}...")
            check_func(connection)
    elif 1 <= choice <= len(sanity_checks):
        check_name, check_func = sanity_checks[choice - 1]
        print(f"\nRunning {check_name}...")
        check_func(connection)
    else:
        print("Invalid choice.")

    connection.close()


if __name__ == "__main__":
    main()
