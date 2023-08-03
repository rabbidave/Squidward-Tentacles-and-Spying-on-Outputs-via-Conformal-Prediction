## ♫ The Dream of the 90's ♫ is alive in ~~Portland~~ ["a weird suite of Enterprise LLM tools"](https://github.com/users/rabbidave/projects/1) named after [Nicktoons](https://en.wikipedia.org/wiki/Nicktoons)
### by [some dude in his 30s](https://www.linkedin.com/in/davidisaacpierce)
#
## Utility 4) # Squidward Tentacles and Spying on Outputs via Conformal Prediction

<img src="https://upload.wikimedia.org/wikipedia/en/thumb/8/8f/Squidward_Tentacles.svg/1200px-Squidward_Tentacles.svg.png" alt="Squidward" title="Squidward" width="40%">

## Description:
A set of serverless functions designed to assist in the monitoring of outputs from language models, specifically inspection of messages for non-conformity to pre-calulcated log-likelihood and the appending of warnings based on the achieved log-likelihood and p-values for new messages

i.e. instead of doing batch or event-driven prediction of the range of possible values, herein we compare individual outputs to previously established outputs and measure non-conformity as a heuristic for whether not not they "would have" fallen outside the expected range

Note: BERT was established as default, given the flexibility in swapping transformers models, but the quality of your model and resultant log-likelihood has a direct effect on the quality of your p-values and their utility as an indicator of non-conformity

#
## Rationale:

1) Large Language Models are [subject to various forms of prompt injection](https://github.com/greshake/llm-security) ([indirect](https://github.com/greshake/llm-security#compromising-llms-using-indirect-prompt-injection) or otherwise); lightweight and step-wise alerting of outputs ensures additional safeguarding of externally facing models
2) User experience, instrumentation, and metadata capture are crucial to the adoption of LLMs for orchestration of [multi-modal agentic systems](https://en.wikipedia.org/wiki/Multi-agent_system); calculating the log-likehood of a given message, and thus it's p-value, serves as a good heuristics for it's adherence to the expected vector space of what might otherwise been previously set as the prediction interval and expected range of values e.g. if you had previously used conformal prediction to establish the possible range of values i.e. instead of doing batch or event-driven prediction of the range of possible values, herein we compare individual outputs to previously established outputs and measure non-conformity as a heuristic for whether not not they "would have" fallen outside the expected range
#
## Intent:

The intent of this Squidward_looking_out_his_window.py is to efficiently spin up, calculate needed values for evaluation, and inspect each message for non-conformity to established output; thereafter routing messages to the appropriate SQS bus (e.g. for response to user, further evaluation, logging, etc)

The goal being to detect if the message has high non-conformity with known model outputs; via use of a pre-calculated log-likelihood for the model (or eventually specific vector space clusters)
    
The is pre-calculated and stored in parquet, then loaded into memory. log-likelihood and p-values are calculated for incoming messages and appended/routed appropriately; when complete the function spins down appropriately. 

Based on the resultant calculations messages are routed to the appropriate SQS bus.

#
### Note: Needs additional error-handling; this is mostly conceptual and assumes the use of environment variables rather than hard-coded values for prediction intervals/p-values. Also contained arbitrary decisions about p-value ties.