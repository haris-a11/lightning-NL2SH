from datasets import load_from_disk

ds = load_from_disk("./data/nl2bash")

train = ds["train"]
val = ds["validation"]
test = ds["test"]

print("train:", len(train))
print("val:", len(val))
print("test:", len(test))

print(train[0])
