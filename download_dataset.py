from datasets import load_dataset

ds = load_dataset("jiacheng-ye/nl2bash")

ds.save_to_disk("./data/nl2bash")

print("dataset saved")
