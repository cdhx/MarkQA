ACTION=${1:-'none'}
exp_id=${2:-'none'}
do_debug=${3:-'False'}

dataset='CWQ'
exp_prefix="exps/gen_multitask/${dataset}_${exp_id}/"

if [ "$ACTION" = "train" ]; then
    
    if [ -d ${exp_prefix} ]; then
        echo "${exp_prefix} already exists"
    else
        mkdir ${exp_prefix}
    fi

    python run_multitask_generator.py \
                            --do_train \
                            --do_eval \
                            --do_predict \
                            --do_debug ${do_debug} \
                            --epochs 1 \
                            --lr 5e-5 \
                            --iters_to_accumulate 1 \
                            --eval_beams 10 \
                            --use_qdt \
                            --add_entity \
                            --pretrained_model_path hfcache/t5-base \
                            --output_dir ${exp_prefix} \
                            --model_save_dir "${exp_prefix}model_saved" \
                            --overwrite_output_dir\
                            --train_batch_size 4 \
                            --eval_batch_size 4 \
                            --test_batch_size 8 | tee "${exp_prefix}log.txt"
elif [ "$ACTION" = "eval" -o "$ACTION" = "predict" ]; then
    predict_split=${4:-'test'}
    python run_multitask_generator.py \
                        --do_eval \
                        --do_predict \
                        --do_debug ${do_debug} \
                        --epochs 2 \
                        --lr 5e-5 \
                        --iters_to_accumulate 1 \
                        --eval_beams 10 \
                        --use_qdt \
                        --add_entity \
                        --pretrained_model_path hfcache/t5-base \
                        --output_dir ${exp_prefix} \
                        --model_save_dir "${exp_prefix}model_saved" \
                        --overwrite_output_dir \
                        --train_batch_size 4 \
                        --eval_batch_size 4 \
                        --test_batch_size 8
else
    echo "train or eval"
fi