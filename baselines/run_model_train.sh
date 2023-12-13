#!/bin/bash
MODEL=$1
pred_type=$2
exp_id=$3
gpu_id=$4


if [ "$MODEL" = "GMT" ]; then 
    cd ./scripts
    conda activate QDTenv
    CUDA_VISIBLE_DEVICES=${gpu_id} ./auto_GMT.sh ${pred_type} ${exp_id}
elif [ "$MODEL" = "T5" ]; then
    cd ./scripts
    conda activate QDTenv
    CUDA_VISIBLE_DEVICES=${gpu_id} ./auto_T5.sh ${pred_type} ${exp_id}
elif [ "$MODEL" = "QDTQA" ]; then
    cd ./models/scripts
    conda activate QDTenv
    CUDA_VISIBLE_DEVICES=${gpu_id} ./auto_QDT.sh ${pred_type} ${exp_id}
else
    echo "Invalid args"
fi
      


