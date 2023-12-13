#!/bin/bash
# generate sparql from question along with qdt

DATA_DIR=../linked_dataset_example #directory of datasets
ENTITY_LINKING_DIR=../linked_dataset_example #directory of entity linking results
DECOMPOSITION_DIR=../linked_dataset_example #directory of decomposition results
dataset="mark"
dataset_version="official"

predict_type=$1   #qdt/subf/sparql
exp_id=$2

exp_prefix="../outputs/${exp_id}_QDT_${predict_type}_${golden_type}/"

if [ -d ${exp_prefix} ]; then
    echo "${exp_prefix} already exists"
else
    mkdir -p ${exp_prefix}
fi

echo "begin training at ${exp_prefix}"
if [ "$predict_type" = "PyQLQDT" ]; then
    pred_type=do_qdt
    max_tgt_len=384 
    batch_sz=8
elif [ "$predict_type" = "PyQL" ]; then
    pred_type=do_subf
    max_tgt_len=384 
    batch_sz=8
else
    pred_type=do_sparql
    max_tgt_len=512
    batch_sz=8
fi

cd ../QDTQA/


if [ -e "${exp_prefix}output/pytorch_model.bin" ]; then
    echo  "Model is ready for evaluation"
else
    python -u run_generator.py \
        --dataset_version ${dataset_version} \
        --data_dir ${DATA_DIR} \
        --entity_linking_result_dir ${ENTITY_LINKING_DIR} \
        --decomposition_result_dir ${DECOMPOSITION_DIR} \
        --dataset ${dataset} \
        --model_type t5 \
        --model_name_or_path "hfcache/t5-base" \
        --do_train \
        --overwrite_output_dir \
        --add_entity \
        --add_relation \
        --${pred_type} \
        --use_qdt \
        --new_qdt \
        --overwrite_cache \
        --max_source_length 256 \
        --max_target_length ${max_tgt_len} \
        --train_file ${DATA_DIR}/${dataset}_train_linked.json \
        --learning_rate 5e-4 \
        --num_train_epochs 5 \
        --logging_steps 1000 \
        --save_steps 100000 \
        --eval_steps 10000 \
        --warmup_ratio 0.1 \
        --output_dir "${exp_prefix}output" \
        --per_device_train_batch_size ${batch_sz} \
        --per_device_eval_batch_size 10 | tee "${exp_prefix}log.txt"
fi
model="${exp_prefix}output"
split="dev"
python -u run_generator.py \
    --dataset_version ${dataset_version} \
    --data_dir ${DATA_DIR} \
    --entity_linking_result_dir ${ENTITY_LINKING_DIR} \
    --decomposition_result_dir ${DECOMPOSITION_DIR} \
    --dataset ${dataset} \
    --model_type t5 \
    --model_name_or_path ${model} \
    --eval_beams 25 \
    --do_eval \
    --add_entity \
    --add_relation \
    --use_qdt \
    --new_qdt \
    --overwrite_cache \
    --${pred_type} \
    --max_source_length 256 \
    --max_target_length ${max_tgt_len} \
    --predict_file ${DATA_DIR}/${dataset}_${split}_linked.json \
    --overwrite_output_dir \
    --output_dir ${exp_prefix}${dataset} \
    --per_device_eval_batch_size 4 \

