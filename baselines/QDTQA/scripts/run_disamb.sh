#!/bin/bash

#Copyright (c) 2021, salesforce.com, inc.
#All rights reserved.
#SPDX-License-Identifier: BSD-3-Clause
#For full license text, see the LICENSE file in the repo root or https://#opensource.org/licenses/BSD-3-Clause

export DATA_DIR=data
ACTION=${1:-none}
dataset="CWQ"
if [ "$ACTION" = "train" ]; then
    exp_id=$2 # experiment id named personally

    exp_prefix="exps/disamb_${dataset}_${exp_id}/"


    if [ -d ${exp_prefix} ]; then
    echo "${exp_prefix} already exists"
    else
    mkdir ${exp_prefix}
    fi

    cp scripts/run_disamb.sh "${exp_prefix}run_disamb.sh"
    git rev-parse HEAD > "${exp_prefix}commitid.log"

    # --overwrite_cache \
    python -u run_disamb.py \
        --dataset ${dataset} \
        --model_type bert \
        --model_name_or_path bert-base-uncased \
        --do_lower_case \
        --do_train \
        --do_eval \
        --disable_tqdm \
        --train_file $DATA_DIR/${dataset}_train_entities.json \
        --predict_file $DATA_DIR/${dataset}_dev_entities.json \
        --learning_rate 1e-5 \
        --evaluate_during_training \
        --num_train_epochs 2 \
        --overwrite_output_dir \
        --max_seq_length 96 \
        --logging_steps 200 \
        --eval_steps 1000 \
        --save_steps 2000 \
        --warmup_ratio 0.1 \
        --output_dir "${exp_prefix}output" \
        --per_gpu_train_batch_size 8 \
        --per_gpu_eval_batch_size 16 | tee "${exp_prefix}log.txt"

elif [ "$ACTION" = "eval" ]; then
    #model=$2
    exp_id=$2 # experiment id named personally
    model="exps/disamb_${dataset}_${exp_id}/output"
    split=${3:-dev}

    python -u run_disamb.py \
        --dataset ${dataset} \
        --model_type bert \
        --model_name_or_path ${model} \
        --do_lower_case \
        --do_eval \
        --predict_file $DATA_DIR/${dataset}_${split}_entities.json \
        --overwrite_output_dir \
        --max_seq_length 96 \
        --output_dir  results/disamb/${dataset}_${split} \
        --per_gpu_eval_batch_size 64

elif [ "$ACTION" = "predict" ]; then
    #model=$2
    exp_id=$2 # experiment id named personally
    model="exps/disamb_${dataset}_${exp_id}/output"
    split=${3:-dev}
    python -u run_disamb.py \
        --dataset ${dataset} \
        --model_type bert \
        --model_name_or_path ${model} \
        --do_lower_case \
        --do_eval \
        --do_predict \
        --predict_file $DATA_DIR/${dataset}_${split}_entities.json \
        --overwrite_output_dir \
        --max_seq_length 96 \
        --output_dir  results/disamb/${dataset}_${split} \
        --per_gpu_eval_batch_size 64
    # copy the entity disambugation file to misc/ directory
    # cp results/disamb/${dataset}_${split}/predictions.json misc/${dataset}_${split}_entity_linking.json
else
    echo "train or eval or predict"
fi