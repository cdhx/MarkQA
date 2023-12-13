#!/bin/bash


export DATA_DIR=data
ACTION=${1:-none}
dataset="CWQ"

if [ "$ACTION" = "train" ]; then
    exp_id=$2

    exp_prefix="exps/gen_${dataset}_${exp_id}/"

    if [ -d ${exp_prefix} ]; then
    echo "${exp_prefix} already exists"
    else
    mkdir ${exp_prefix}
    fi

    cp scripts/run_gen.sh "${exp_prefix}run_gen.sh"
    git rev-parse HEAD > "${exp_prefix}commitid.log"

    python -u run_generator.py \
        --data_dir ${DATA_DIR} \
        --dataset ${dataset} \
        --model_type t5 \
        --model_name_or_path t5-base \
        --do_lower_case \
        --do_train \
        --do_eval \
        --overwrite_cache \
        --overwrite_output_dir \
        --train_file ${DATA_DIR}/${dataset}_train_expr.json \
        --predict_file ${DATA_DIR}/${dataset}_dev_expr.json \
        --learning_rate 3e-5 \
        --num_train_epochs 10 \
        --logging_steps 1000 \
        --eval_steps 5000 \
        --save_steps 5000 \
        --warmup_ratio 0.1 \
        --output_dir "${exp_prefix}output" \
        --eval_beams 10 \
        --per_device_train_batch_size 16 \
        --per_device_eval_batch_size 16 | tee "${exp_prefix}log.txt"
        

elif [ "$ACTION" = "eval" -o "$ACTION" = "predict" ]; then
    exp_id=$2
    # echo $exp_id
    model="exps/gen_CWQ_${exp_id}/output"
    # echo $model
    #model=$2
    split=${3:-dev}
    
    # -u : force the binary I/O layers of stdout and stderr to be unbuffered;
    python -u run_generator.py \
        --data_dir ${DATA_DIR} \
        --dataset ${dataset} \
        --model_type t5 \
        --model_name_or_path ${model} \
        --eval_beams 10 \
        --do_lower_case \
        --do_eval \
        --overwrite_cache \
        --predict_file ${DATA_DIR}/${dataset}_${split}_expr.json \
        --overwrite_output_dir \
        --output_dir results/gen/${dataset}_${split}_${exp_id} \
        --per_device_eval_batch_size 8     
else
    echo "train or eval"
fi
