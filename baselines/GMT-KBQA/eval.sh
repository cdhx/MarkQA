#!/bin/bash
conda activate QDTenv
python eval_topk_prediction_final.py --dataset="num_12k_shuffle_split_rewriting" --split="dev" --pred_type="qdt" \
    --pred_file="exps/CWQ_gmt_concat_golden_ent_rel_numeral_predict_qdt_rewriting_20_epoch_0509/beam_25_num_dev_3_top_k_predictions.json"


python eval_topk_prediction_final.py --dataset="num_12k_shuffle_split_rewriting" --split="dev" --pred_type="qdt" \
    --pred_file="/home/yhbao/numeral_qa/models/GMT-KBQA/exps/qdt_test/beam_25_num_dev_3_top_k_predictions.json"


python eval_topk_prediction_final.py --dataset="num_12k_shuffle_split_rewriting" --split="dev" --pred_type="subf" \
    --pred_file="/home/yhbao/numeral_qa/models/GMT-KBQA/exps/subf_test/beam_25_num_dev_6_top_k_predictions.json"


python eval_topk_prediction_final.py --dataset="num_12k_shuffle_split_rewriting" --split="dev" --pred_type="sparql" \
    --pred_file="/home/yhbao/numeral_qa/models/GMT-KBQA/exps/sparql_test/beam_25_num_dev_6_top_k_predictions.json"


python eval_topk_prediction_final.py --dataset="num_12k_shuffle_split_rewriting" --split="dev" --pred_type="qdt" \
    --pred_file="/home/yhbao/numeral_qa/models/GMT-KBQA/exps/qdt_test_golden/beam_25_num_dev_3_top_k_predictions.json"

python eval_topk_prediction_final.py --dataset="processed_replaced_0516_incremental_normed" --split="dev" --pred_type="qdt" \
    --pred_file="/home/yhbao/numeral_qa/models/GMT-KBQA/exps/test_debug/processed_replaced_0516_incremental_normed_dev.json"

python eval_topk_prediction_final.py --dataset="mrak_0606" --split="dev" --pred_type="qdt" \
    --pred_file="/home/yhbao/numeral_qa/models/GMT-KBQA/exps/CWQ_mrak_0606_qdt_golden/beam_25_test_4_top_k_predictions.json"