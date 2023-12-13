#!/bin/bash
# generate sparql from question along with qdt

export DATA_DIR=data
ACTION=${1:-none}
dataset="CWQ"

if [ "$ACTION" = "train" ]; then
    exp_id=$2

    exp_prefix="exps/qdtgen_${dataset}_${exp_id}/"

    if [ -d ${exp_prefix} ]; then
    echo "${exp_prefix} already exists"
    else
    mkdir -p ${exp_prefix}
    fi

    cp scripts/run_qdtgen.sh "${exp_prefix}run_qdtgen.sh"
    git rev-parse HEAD > "${exp_prefix}commitid.log"

    # --model_name_or_path t5-base \
    # --cache_dir "hfcache/t5-base"
    # --overwrite_cache
    # --add_relation \
    python -u run_qdt_generator.py \
        --data_dir ${DATA_DIR} \
        --dataset ${dataset} \
        --model_type t5 \
        --model_name_or_path "hfcache/t5-base" \
        --do_lower_case \
        --do_train \
        --do_eval \
        --overwrite_output_dir \
        --overwrite_cache \
        --train_file ${DATA_DIR}/qdt/${dataset}_train_qdt_linear.json \
        --predict_file ${DATA_DIR}/qdt/${dataset}_dev_qdt_linear.json \
        --learning_rate 3e-5 \
        --num_train_epochs 15 \
        --logging_steps 1000 \
        --eval_steps 5000 \
        --save_steps 5000 \
        --warmup_ratio 0.1 \
        --output_dir "${exp_prefix}output" \
        --eval_beams 5 \
        --per_device_train_batch_size 16 \
        --per_device_eval_batch_size 16 | tee "${exp_prefix}log.txt"
        

elif [ "$ACTION" = "eval" -o "$ACTION" = "predict" ]; then
    exp_id=$2
    # echo $exp_id
    model="exps/qdtgen_${dataset}_${exp_id}/output"
    # echo $model
    #model=$2
    split=${3:-dev}
    
    
    # -u : force the binary I/O layers of stdout and stderr to be unbuffered;
    # --add_relation
    # --overwrite_cache \ 
    python -u run_qdt_generator.py \
        --data_dir ${DATA_DIR} \
        --dataset ${dataset} \
        --model_type t5 \
        --model_name_or_path ${model} \
        --eval_beams 5 \
        --do_lower_case \
        --do_eval \
        --overwrite_cache \
        --predict_file ${DATA_DIR}/qdt/${dataset}_${split}_all_qdt_linear.json \
        --overwrite_output_dir \
        --output_dir results/qdtgen/${dataset}_${split}_${exp_id} \
        --per_device_eval_batch_size 16 
else
    echo "train or eval"
fi
