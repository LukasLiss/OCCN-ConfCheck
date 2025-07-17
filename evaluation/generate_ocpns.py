from collections import Counter
import time
import pm4py
import os

from pm4py.objects.ocpn import factory as ocpn_factory
from pm4py.objects.ocpn import converter as ocpn_converter
from pm4py.algo.simulation.playout.ocpn.variants.extensive import (
    apply as playout_ocpn_extensive,
)
from pm4py.objects.ocpn.obj import OCMarking

def generate_ocpns():
    ocels = ["ContainerLogistics.json"]
    ocel_paths = [os.path.join("evaluation", "event_logs", el) for el in ocels]
    print("Generating OCPNs from OCELs...")
    # create discovered_ocpns directory if it doesn't exist
    if not os.path.exists("evaluation/discovered_ocpns"):
        os.makedirs("evaluation/discovered_ocpns")
    for ocel_path in ocel_paths:
        # discover ocpn
        print(f"Processing {ocel_path}...")
        ocel = pm4py.read_ocel2(ocel_path)
        ocpn = pm4py.discover_oc_petri_net(ocel)
        path_png = os.path.join(
            "evaluation", "discovered_ocpns", f"{os.path.basename(ocel_path)}.png"
        )
        pm4py.save_vis_ocpn(ocpn, path_png)
        print(f"Discovered OCPN for {ocel_path} and saved visualization to {path_png}")

        # convert to OCPetriNet object
        ocpn_obj = ocpn_factory.create(ocpn)
        ocpn_obj_converted_back = ocpn_converter.apply(
            ocpn_obj, variant=ocpn_converter.Variants.TO_ALTERNATIVE_FORMAT
        )
        path_png_converted = os.path.join(
            "evaluation",
            "discovered_ocpns",
            f"{os.path.basename(ocel_path)}_converted.png",
        )
        pm4py.save_vis_ocpn(ocpn_obj_converted_back, path_png_converted)
        print(
            f"Discovered OCPN for {ocel_path} and saved visualization to {path_png_converted}"
        )

        # get source & target places
        source_places = {}
        sink_places = {}
        for place in ocpn_obj.places:
            if place.name.endswith("source"):
                source_places[place.object_type] = place
            elif place.name.endswith("sink"):
                sink_places[place.object_type] = place


        
            

        # play-out TODO hardcoded for 1 example here
        counters = {
            "Customer Order": Counter([f"customer_order_{i}" for i in range(1)]),
            "Transport Document": Counter([f"transport_document_{i}" for i in range(1)]),
            "Vehicle": Counter([f"vehicle_{i}" for i in range(1)]),
            "Container": Counter([f"container_{i}" for i in range(2)]),
            "Truck": Counter([f"truck_{i}" for i in range(1)]),
            "Handling Unit": Counter([f"handling_unit_{i}" for i in range(2)]),
            "Forklift": Counter([f"forklift_{i}" for i in range(1)]),
        }

        initial_marking = {
            source_places[obj_type]: counters[obj_type]
            for obj_type in counters
        }
        
        final_marking = {
            sink_places[obj_type]: counters[obj_type]
            for obj_type in counters
        }
        
        # perform the play-out
        print("Performing play-out...")
        
        params = {
            "return_traces": True,
            "maxBindingsPerActivity": 10,
            "branchingFactorTransitions": 1,
            "branchingFactorBindings": 1,
        }
        
        no_traces_acc = 0
        
        def print_traces(traces, idx_to_transition):
            # convert transition indices to labels
            for i, trace in enumerate(traces):
                trace_list = []
                for event in trace:
                    if idx_to_transition[event[0]].label:
                        trace_list.append((idx_to_transition[event[0]].label, event[1]))
                traces[i] = tuple(trace_list)

            print(len(traces))
            for i in range(len(traces)):
                print(f"Trace {i}:")
                for event in traces[i]:
                    print(f"\t{event}")
        
        for i in range(1):
            branching_factor = 1.4
            params["branchingFactorTransitions"] = branching_factor
            params["branchingFactorBindings"] = branching_factor
            print(f"branchingFactorTransitions = branchingFactorTransitions = {branching_factor}")
            start = time.time()
            (traces, idx_to_transition) = playout_ocpn_extensive(
                ocpn_obj, OCMarking(initial_marking), OCMarking(final_marking), parameters=params
            )
            diff = time.time() - start
            print(f"Time taken for extensive playout: {diff} seconds")
            no_traces_acc += len(traces)
            print("Number of traces generated:", len(traces))
            print("Number of traces generated (accumulated):", no_traces_acc)
            print("############")
            if len(traces) > 0:
                print_traces(traces[:1], idx_to_transition)


if __name__ == "__main__":
    generate_ocpns()
