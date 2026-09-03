from app.services.policy_retriever import retrieve_policies


def main():
    query = """
    Payment failed because of a temporary issuer error.
    We want to retry the payment but must respect retry limits.
    """

    policies = retrieve_policies(query)

    print("\nRetrieved policies:")
    print("=" * 60)

    for policy in policies:
        print(f"\n[{policy['id']}] {policy['title']}")
        print(policy["content"].strip())


if __name__ == "__main__":
    main()