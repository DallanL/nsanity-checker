import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os


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
        else:
            print(
                "All entries in huntgroup_entry_config have a corresponding huntgroup in huntgroup_config."
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
    if connection:
        check_dial_rules_have_dialplan(connection)
        check_dialplans_have_domain(connection)
        check_domains_have_reseller(connection)
        check_huntgroup_agents_have_huntgroup(connection)
        connection.close()
    else:
        print("Failed to connect to the database.")


if __name__ == "__main__":
    main()
