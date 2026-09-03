RECOVERY_POLICIES = [
    {
        "id": "PAYMENT_TRANSIENT_001",
        "title": "Transient Payment Failure",
        "category": "payment_failure",
        "content": """
        If a payment fails because of a transient or temporary failure,
        the recovery agent may retry the payment.

        Examples of transient failures include temporary issuer errors,
        gateway timeouts, temporary network failures, and service
        interruptions.

        The agent should not retry indefinitely.
        Maximum automated retry attempts: 2.
        """,
    },

    {
        "id": "PAYMENT_REPEATED_001",
        "title": "Repeated Payment Failure",
        "category": "payment_failure",
        "content": """
        If the same payment continues to fail after automated retries,
        the agent must stop retrying.

        The case should be escalated to an alternate recovery action
        such as customer notification or manual review.

        Repeated failures must be recorded in the audit trail.
        """,
    },

    {
        "id": "HIGH_VALUE_001",
        "title": "High Value Transaction",
        "category": "risk_control",
        "content": """
        High-value transactions require conservative recovery behavior.

        The agent should avoid aggressive automated actions when the
        amount at risk is unusually high.

        High-value cases may be escalated for manual review depending
        on the confidence of the recovery decision.
        """,
    },

    {
        "id": "CUSTOMER_CONTACT_001",
        "title": "Customer Contact Frequency",
        "category": "customer_contact",
        "content": """
        The recovery agent must avoid excessive customer contact.

        If a customer has already been contacted during the current
        recovery cycle, the agent should not send another identical
        notification.

        Customer-facing actions must be auditable.
        """,
    },

    {
        "id": "RECOVERY_STOP_001",
        "title": "Recovery Stopping Rules",
        "category": "stopping_rule",
        "content": """
        Every recovery workflow must have a stopping condition.

        Stop the workflow when:
        1. Payment succeeds.
        2. The recovery amount is successfully recovered.
        3. Maximum retry attempts are reached.
        4. The case is escalated for manual intervention.
        5. The transaction is determined to be unrecoverable.

        The agent must never continue recovery indefinitely.
        """,
    },

    {
        "id": "AUDIT_001",
        "title": "Recovery Audit Requirement",
        "category": "compliance",
        "content": """
        Every autonomous recovery decision must create an audit event.

        The audit record should contain:
        - reason for the decision
        - selected action
        - relevant policy
        - outcome
        - stopping condition

        Recovery actions must be explainable after execution.
        """,
    },
]