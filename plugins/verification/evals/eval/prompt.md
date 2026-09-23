---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our customer-support bot for a bike shop is an LLM app. Nobody has reviewed its conversations yet; here are three from last week's export:

1. User: "Can I return a helmet I wore once?" Bot: "Yes! All items can be returned within 30 days, no questions asked."
2. User: "Do you service e-bikes?" Bot: "We service all bikes. Book at shop.example/service." User: "The page says no e-bikes." Bot: "Sorry for the confusion! We service all bikes."
3. User: "What size frame for 180 cm?" Bot: "A 56 cm road frame or a large mountain frame usually fits 178-185 cm."

Write the LLM-as-judge prompt that scores the quality of the bot's answers, so we can track it every week. Just the prompt, please.
