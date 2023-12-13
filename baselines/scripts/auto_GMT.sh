
predict_type=$1   #qdt/subf/sparql
exp_id=$2

mrak_version="official"
dataset_dir=../linked_dataset_example #directory of mark dataset (linked)
predict_split="dev"


exp_prefix="../outputs/${exp_id}_GMT_${predict_type}_${golden_type}/"


cd ../GMT-KBQA
if [ -d ${exp_prefix} ]; then
    echo "${exp_prefix} already exists"
else
    mkdir -p ${exp_prefix}
fi

echo "begin training at ${exp_prefix}"
if [ "$predict_type" = "PyQLQDT" ]; then
    pred_type=do_qdt
    max_target_len=384
    batch_sz=8
elif [ "$predict_type" = "PyQL" ]; then
    pred_type=do_subf
    max_target_len=384
    batch_sz=6
else
    pred_type=do_sparql
    max_target_len=512
    batch_sz=4
fi

if [ -e "${exp_prefix}model_saved/pytorch_model.bin" ]; then
    echo  "Model is ready for evaluation"
    python run_multitask_generator_final.py \
                            --${pred_type} \
                            --do_predict \
                            --dataset_dir ${dataset_dir} \
                            --predict_split ${predict_split} \
                            --max_tgt_len ${max_target_len} \
                            --max_src_len 256 \
                            --epochs 40 \
                            --mrak_version ${mrak_version} \
                            --lr 5e-5 \
                            --eval_beams 25 \
                            --iters_to_accumulate 1 \
                            --pretrained_model_path t5-base \
                            --output_dir ${exp_prefix} \
                            --model_save_dir "${exp_prefix}model_saved" \
                            --overwrite_output_dir \
                            --normalize_relations \
                            --sample_size 10 \
                            --add_prefix \
                            --model T5_MultiTask_Relation_Entity_Concat \
                            --warmup_epochs 5 \
                            --train_batch_size ${batch_sz} \
                            --eval_batch_size 2 \
                            --test_batch_size 2 | tee "${exp_prefix}log_eval.txt"
else
    python run_multitask_generator_final.py \
                            --do_train \
                            --${pred_type} \
                            --dataset_dir ${dataset_dir} \
                            --do_predict \
                            --predict_split ${predict_split} \
                            --max_tgt_len ${max_target_len} \
                            --max_src_len 256 \
                            --mrak_version ${mrak_version} \
                            --epochs 40 \
                            --lr 5e-5 \
                            --eval_beams 25 \
                            --iters_to_accumulate 1 \
                            --pretrained_model_path t5-base \
                            --output_dir ${exp_prefix} \
                            --model_save_dir "${exp_prefix}model_saved" \
                            --overwrite_output_dir \
                            --normalize_relations \
                            --sample_size 10 \
                            --add_prefix \
                            --model T5_MultiTask_Relation_Entity_Concat \
                            --warmup_epochs 5 \
                            --train_batch_size ${batch_sz} \
                            --eval_batch_size 4 \
                            --test_batch_size 4 | tee "${exp_prefix}log_eval.txt"
fi