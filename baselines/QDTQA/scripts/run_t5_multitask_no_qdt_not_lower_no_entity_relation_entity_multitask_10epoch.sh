ACTION=${1:-none}
exp_id=${2:-none}
do_debug=${3:-False}

dataset='CWQ'
exp_prefix="exps/gen_multitask/${dataset}_${exp_id}/"


if [ "$ACTION" = "train" ]; then
    
    if [ -d ${exp_prefix} ]; then
        echo "${exp_prefix} already exists"
    else
        mkdir ${exp_prefix}
    fi
    # --do_eval \
    python run_multitask_generator.py \
                            --do_train \
                            --do_predict \
                            --do_eval \
                            --do_debug ${do_debug} \
                            --epochs 10 \
                            --lr 5e-5 \
                            --eval_beams 50 \
                            --iters_to_accumulate 1 \
                            --pretrained_model_path /home2/xxhu/QDT2SExpr/CWQ/hfcache/t5-base \
                            --entity_multitask \
                            --output_dir ${exp_prefix} \
                            --model_save_dir "${exp_prefix}model_saved" \
                            --overwrite_output_dir\
                            --train_batch_size 4 \
                            --eval_batch_size 4 \
                            --test_batch_size 2 | tee "${exp_prefix}log.txt"
elif [ "$ACTION" = "eval" -o "$ACTION" = "predict" ]; then
    split=${4:-test}
    beam_size=${5:-10}
    test_batch_size=${6:-8}
    echo "Predicting ${split} with beam_size: ${beam_size} and batch_size: ${test_batch_size}"
    python run_multitask_generator.py \
                        --do_predict \
                        --do_debug ${do_debug} \
                        --predict_split ${split} \
                        --epochs 2 \
                        --lr 5e-5 \
                        --entity_multitask \
                        --iters_to_accumulate 1 \
                        --eval_beams ${beam_size} \
                        --pretrained_model_path /home2/xxhu/QDT2SExpr/CWQ/hfcache/t5-base \
                        --output_dir ${exp_prefix} \
                        --model_save_dir "${exp_prefix}model_saved" \
                        --overwrite_output_dir \
                        --train_batch_size 4 \
                        --eval_batch_size 4 \
                        --test_batch_size ${test_batch_size}
else
    echo "train or eval"
fi