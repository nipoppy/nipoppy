import subprocess
import argparse

def run(global_config, output_dir, participant_id, session_id):
    
    DATASET_ROOT = global_config["DATASET_ROOT"]
    CONTAINER_STORE = global_config["CONTAINER_STORE"]
    #is currently mriqc_patch.simg
    MRIQC_CONTAINER = global_config["PROC_PIPELINES"]["mriqc"]["CONTAINER"]

    # config = json.load(open(args.global_config))

    subprocess.run([f"echo subject: {participant_id} session: {session_id} >> {output_dir}/mriqc_out_{participant_id}.log"], shell=True)

    subprocess.run([f"singularity run --cleanenv -B {DATASET_ROOT}:/data:ro -B {output_dir}:/out {CONTAINER_STORE}/{MRIQC_CONTAINER} \
                --no-sub /data /out participant --participant-label {participant_id} --session-id {session_id} \
                >> {output_dir}/mriqc_out_{participant_id}.log"], shell=True)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')

    parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
    parser.add_argument('--output_dir', type=str, help='overwrite path to put results in case of issues with default')
    parser.add_argument('--participant_id', type=str, help='subject ID to be processed')
    parser.add_argument('--session_id', type=str, help='session ID to be processed')

    args = parser.parse_args()
    
    run(global_config=args.global_config, output_dir=args.output_dir, participant_id=args.participant_id, session_id=args.session_id)
