# LeakTrace

LeakTrace is a local Streamlit demo that fingerprints a memo for a recipient by changing synonym choices, embeds the personalized memo in an image, and traces a pasted copy from its wording.

## Run locally

Use Python 3.10 or newer. From the repository directory, run these commands in a virtual environment.

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Run `python test_all.py` to check all 255 fingerprint IDs and the PNG round trip for three recipients with both image methods.

## Demo

1. In **Sender**, use the example memo, select Asha and DCT, and download the PNG. The preview shows the changed wording, capacity, PSNR, and amplified pixel differences.
2. In **Recipient**, upload the PNG or use the latest image from Sender. Select the same method, click **Extract**, and copy the recovered memo.
3. In **Leak Trace**, paste the memo and click **Trace leak**. The table shows the observed synonyms and bits. Try again with Ravi or Neha to see a different match.

![Sender showing the original and personalized memos and the cover, stego, and difference images](docs/sender.png)

![Recipient displaying the recovered memo and JPEG compression results](docs/recipient.png)

![Leak Trace showing the synonym table and the result for Asha](docs/trace.png)

## JPEG recompression results

The table counts exact memo recoveries out of three using the example memo personalized for Asha, Ravi, and Neha. Each method embedded the memos separately in the bundled 1280 × 1280 cover. Pillow saved each stego image as JPEG at the listed quality with its default subsampling.

| JPEG quality | LSB | DCT |
| --- | --- | --- |
| 95 | 0/3 | 3/3 |
| 85 | 0/3 | 3/3 |
| 75 | 0/3 | 3/3 |

The Recipient tab can repeat the experiment on one image at a time. Use the same cover and memo when comparing separately generated LSB and DCT images. Results depend on the cover and JPEG encoder. Use the downloaded PNG to preserve the embedded data.

## Limitations

- The prototype stores a single 8-bit ID in eight synonym pairs. Missing or tied pairs leave the ID incomplete. Paraphrasing or comparing multiple personalized copies can expose, remove, or change the fingerprint.
- A matching ID identifies wording associated with a distributed copy. The prototype cannot establish who shared it.
- The hidden memo is plaintext. The image payload has a length header and a UTF-8 check. Some image changes can produce altered text that still decodes.
- LSB is fragile under recompression and resizing. DCT has lower capacity and can also fail when an image is edited.

Sample cover by the NASA Apollo 17 crew, public domain in the United States. [The Blue Marble, AS17-148-22727](https://commons.wikimedia.org/wiki/File:The_Blue_Marble,_AS17-148-22727.jpg)
