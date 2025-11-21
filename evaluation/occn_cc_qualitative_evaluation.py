import datetime
import os
from typing import Set
import pm4py
from pm4py.objects.ocpn import factory as ocpn_factory
from pm4py.algo.occn_evaluation.replay_fitness import algorithm as occn_fitness
from pm4py.objects.ocpn.exporter import exporter as ocpn_exporter
from discover_occn import discover_occn_from_ocel


def read_top_variants(file_path) -> Set[str]:
    """
    Reads the event ids corresponding to the top variants from a given file.

    Parameters
    ----------
    file_path : str
        Path to the file containing event ids of top variants.

    Returns
    -------
    Set[str]
        Set of event ids corresponding to the top variants.
    """
    with open(file_path, "r") as f:
        event_ids = {line.strip() for line in f.readlines()}
    return event_ids

def dump_ocpn(ocpn, file_name, directory):
    """
    Serializes the given OCPN object to a JSON file in the specified directory.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, file_name)
    ocpn_exporter.apply(ocpn, file_path, variant=ocpn_exporter.Variants.JSON_BRIDGE)
    
def create_occn_output_file(directory_path, cols, ocel_name):
    """
    Creates an output file for OCCN fitness results in the specified directory.
    
    Parameters
    ----------
    directory_path : str
        Path to the directory where the output file will be created.
    cols : List[str]
        List of column names for the output file.
    ocel_name : str
        Name of the OCEL file used for naming the output file.  
    
    Returns
    -------
    str
        Path to the created output file.
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file_path = os.path.join(directory_path, f"{now_str}_{ocel_name}_occn_fitness_results.csv")
    with open(output_file_path, "w") as f:
        f.write(",".join(cols) + "\n")
    return output_file_path

def add_occn_results_to_file(output_file_path, results_dict, no_variants):
    """
    Appends OCCN fitness results to the specified output file.
    
    Parameters
    ----------
    output_file_path : str
        Path to the output file.
    results_dict : Dict[str, Any]
        Dictionary containing OCCN fitness results to be appended.
    no_variants : int
        Number of top variants used for mining the OCCN.
    """
    with open(output_file_path, "a") as f:
        row = f"{no_variants},{results_dict['log_fitness']},{results_dict['no_process_executions']}"
        f.write(row + "\n")

if __name__ == "__main__":
    # Read OCEL
    ocel_name = "ocel2-p2p.json"
    ocel_path = os.path.join("evaluation", "event_logs", ocel_name)
    ocel = pm4py.read_ocel2(ocel_path)

    # Create output file for OCCN fitness results
    out_file = create_occn_output_file(os.path.join("evaluation", "occn_cc_qualitative_evaluation_results", "data"), ["no_top_variants", "log_fitness", "no_process_executions"], ocel_name)

    # Compuet fitness for top k variants    
    for k in range(1, 400):
        print(f"\nEvaluating top {k} variants...")
        # Read top variants
        top_variants_file = os.path.join(
            "evaluation", "assets", "ocel2-p2p", f"ocel2-p2p_top_{k}_variants_event_ids.txt"
        )
        top_event_ids = read_top_variants(top_variants_file)

        # Filter OCEL to only include top variants
        ocel_filtered = pm4py.filter_ocel_events(ocel, top_event_ids, positive=True)

        print("Number of events in filtered OCEL:", len(ocel_filtered.events))
        print("Number of objects in filtered OCEL:", len(ocel_filtered.objects))

        # Mine OCPN
        ocpn = pm4py.discover_oc_petri_net(ocel_filtered)
        # Save viz
        if not os.path.exists("evaluation/discovered_ocpns"):
            os.makedirs("evaluation/discovered_ocpns")
        path_png = os.path.join(
            "evaluation", "discovered_ocpns", f"{os.path.basename(ocel_path)}.png"
        )
        pm4py.save_vis_ocpn(ocpn, path_png)

        # Transform to OCPN object
        ocpn = ocpn_factory.create(ocpn)
        
        # Serialize OCPN to JSON file
        dump_ocpn(ocpn, f"{os.path.basename(ocel_path)}_ocpn_top_{k}_variants.json", "evaluation/discovered_ocpns/serialized")
        
        # Mine OCCN with 0 threshold
        occn = discover_occn_from_ocel(ocel_filtered, ocel_name, 0)
        
        # Compute OCCN fitness
        occn_results = occn_fitness.apply(occn, ocel)
        print("OCCN Fitness Results:")
        print(f"log_fitness: {occn_results['log_fitness']}")
        print(f"no_process_executions: {occn_results['no_process_executions']}")
        # Append results to output file
        add_occn_results_to_file(out_file, occn_results, k)
    
