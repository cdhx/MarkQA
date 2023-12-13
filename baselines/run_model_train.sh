#!/bin/bash
MODEL=$1
pred_type=$2
golden_setting=$3
exp_id=$4
gpu_id=$5


current_path=$(pwd)

echo "Current Path: $current_path"


if [ "$MODEL" = "GMT" ]; then 
    cd ./scripts
    conda activate qdt
    CUDA_VISIBLE_DEVICES=${gpu_id} ./auto_GMT.sh ${golden_setting} ${pred_type} ${exp_id}
elif [ "$MODEL" = "T5" ]; then
    cd ./scripts
    conda activate qdt
    CUDA_VISIBLE_DEVICES=${gpu_id} ./auto_T5.sh ${golden_setting} ${pred_type} ${exp_id}
elif [ "$MODEL" = "QDTQA" ]; then
    cd ./models/scripts
    conda activate qdt
    CUDA_VISIBLE_DEVICES=${gpu_id} ./auto_QDT.sh ${golden_setting} ${pred_type} ${exp_id}
else
    echo "Invalid args"
fi
      


