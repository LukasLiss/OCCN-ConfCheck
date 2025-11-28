# Object-centric Conformance Checking on Object-Centric Causal Nets

This repository contains the implementation for an object-centric conformance checking approach that works on object-centric causal nets.

The algorithm enables:

1.  Computing the fitness of an object-centric event log (OCEL 2.0) for an object-centric causal net.
2.  Checking whether a set of objects is in the language of an object-centric causal net

This repository is a fork of the open-source process mining library [pm4py](https://github.com/process-intelligence-solutions/pm4py) and is extended with our contributions, including the conformance checking approach for object-centric causal nets.

## Evaluation

The qualitative and quantitative evaluation is explained in the following.

### Quantitative Evaluation
We used two object-centric event log, namely procure-to-pay (P2P) and container logistics and the two case-centric event logs road traffic fine log and the BPI 2017 challenge.
The code for teh runtime evaluation can be found in the occn_cc_quantitative_evaluation.py.

### Qualitative Evaluation

The publicly accessible Procure-to-Pay P2P event log was used for the evaluation. The top 3 most frequent variants were used to compute the normative process models (one object-centric causal net and one object-centric Petri net). Then the the fitness of the complete log was computed using object-centric alignments for the object-centric Petri net and our implementation for the object-centric causal net.

Our approach detected 20 deviating process executions more than the ocpn-alignment approach. This is due to the modeling capabilities of the undelying models, where occn can model things like concrete cardinalities that ocpns currently not model and thus, these deviation are also not detected.

The code for the qualitative evaluation can be found in the occn_cc_qualitative_evaluation.py.

### Evaluated Object-Centric Datasets (OCELs)

The following publicly accessible dataset were used in the evaluation:

1.  **Container Logistics:** A real-world logistics log from the [OCEL standard website](https://ocel-standard.org/event-logs/simulations/logistics/).
2.  **Procure-to-Pay (P2P):** A classic P2P example log from the [OCEL standard website](https://ocel-standard.org/event-logs/simulations/p2p/).


## Installation

To set up your environment and run the code, please follow these steps:

1.  **Create and activate a virtual environment:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    # On Windows, use: .venv\Scripts\activate
    ```

2.  **Install pm4py dependencies:**

    ```bash
    pip install -r requirements_complete.txt
    ```

3.  **Install this forked version of pm4py in editable mode:**

    ```bash
    pip install -e .
    ```

4.  **Install additional packages:**

    ```bash
    pip install rich
    ```
