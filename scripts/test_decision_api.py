from openai import OpenAI

client = OpenAI()
decision = client.decisions.create(
    model="gpt-6-luna",
    input="I was charged twice for my subscription this month. Could you help me get a refund for the extra charge?",
    questions=[
        {
            "type": "choice",
            "instructions": "Which team should handle this customer request? Choose the team that best matches the customer's main concern.",
            "choices": [
                {
                    "value": "Billing"
                },
                {
                    "value": "Technical support"
                },
                {
                    "value": "Sales"
                }
            ]
        }
    ],
)
print(decision.answers)
