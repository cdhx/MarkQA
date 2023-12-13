predict_type=$1   #qdt/subf/sparql
exp_id=$2

mrak_version="official"
dataset_dir=../linked_dataset_example #directory of mark dataset (linked)
predict_split="dev"


exp_prefix="../outputs/${exp_id}_T5_${predict_type}_${golden_type}/"

cd ../GMT-KBQA
if [ -d ${exp_prefix} ]; then
    echo "${exp_prefix} already exists"
else
    echo "begin training at ${exp_prefix}"
    mkdir -p ${exp_prefix}
fi
if [ "$predict_type" = "PyQLQDT" ]; then
    pred_type=do_qdt
    max_tgt_len=384
    train_bs=8
elif [ "$predict_type" = "PyQL" ]; then
    pred_type=do_subf
    max_tgt_len=384
    train_bs=8
else
    pred_type=do_sparql
    max_tgt_len=512
    train_bs=4
fi



if [ -e "${exp_prefix}model_saved/pytorch_model.bin" ]; then
    echo  "Model is ready for evaluation"
    python run_multitask_generator_final.py \
                            --mrak_version ${mrak_version} \
                            --dataset_dir ${dataset_dir} \
                            --do_predict \
                            --predict_split ${predict_split} \
                            --max_tgt_len ${max_tgt_len} \
                            --max_src_len 256 \
                            --lr 5e-5 \
                            --${pred_type} \
                            --eval_beams 25 \
                            --iters_to_accumulate 1 \
                            --pretrained_model_path t5-base \
                            --output_dir ${exp_prefix} \
                            --model_save_dir "${exp_prefix}model_saved" \
                            --overwrite_output_dir \
                            --normalize_relations \
                            --sample_size 10 \
                            --model T5_generation_concat \
                            --train_batch_size ${train_bs} \
                            --eval_batch_size 4 \
                            --test_batch_size 4 | tee "${exp_prefix}log.txt"
else
    python run_multitask_generator_final.py \
                            --mrak_version ${mrak_version} \
                            --dataset_dir ${dataset_dir} \
                            --do_train \
                            --do_predict \
                            --predict_split ${predict_split} \
                            --max_tgt_len ${max_tgt_len} \
                            --max_src_len 256 \
                            --epochs 30 \
                            --lr 5e-5 \
                            --${pred_type} \
                            --eval_beams 25 \
                            --iters_to_accumulate 1 \
                            --pretrained_model_path t5-base \
                            --output_dir ${exp_prefix} \
                            --model_save_dir "${exp_prefix}model_saved" \
                            --overwrite_output_dir \
                            --normalize_relations \
                            --sample_size 10 \
                            --model T5_generation_concat \
                            --train_batch_size ${train_bs} \
                            --eval_batch_size 4 \
                            --test_batch_size 4 | tee "${exp_prefix}log.txt"
fi