# TODO:
* LIST OF CHANNELS ARE RANDOM FOR NOW - TODO REVIEW their correct political BIAS
* Workflow for deployment .exe files requires fix. I dont have time for that. Maybe later. Sorry

# User Manual for the "Download Telegram Posts" Application

This application is used to download posts from Telegram channels and save them to text files.

## 1. Preparing the Channel List:

* **Recommendation:** Create *two* separate channel lists in `.txt` files. You can divide them thematically (e.g., "news", "sport", "technology") or by *political bias* (e.g., "pro-Russian", "pro-Ukrainian", "neutral"). Such division will facilitate later analysis.
* Each channel should be on a separate line, either as a full URL (e.g., `https://t.me/channel_name`) or just the name (e.g., `channel_name`). ***Do not* add a '/' character at the end of the channel name**.
* If you have channels in the full URL format, the program will automatically remove everything before the last '/' and retrieve only the channel name.
* The program includes a sample list of over 160 channels, but these are just examples. You need to create your actual list yourself[cite: 2, 3, 4, 5, 6].

![{AD1F8859-3306-4393-9B14-A80DD1DE3A03}](https://github.com/user-attachments/assets/36ba23a4-fad8-4935-9bdf-cbc9ccbe3f8a)


## 2. Launching the Application:

* After launching the application, you will see the main program window.
<img width="671" alt="{A47CC81A-BCCB-4408-B63E-3492D3A2BB2C}" src="https://github.com/user-attachments/assets/582817d3-d351-423c-9f15-15c93bb5aa73" />




## 3. Configuration:

* **Select Channel File:**
    * Click the "Browse..." button.
    * In the dialog window, select the `.txt` file containing the channel list.
    * The path to the selected file will appear in the text field.

* **Select Date:**
    * Choose the desired date or date range using the provided options (Specific Date, Date Range, Today, Yesterday, All).

## 4. Downloading Posts:

* Click the relevant "Download..." button based on your date selection.
* The application will start downloading posts from the channels listed in the selected file.
* **Logs (what's happening):** In the lower part of the window, in the "Logs" field, informational messages about the progress will be displayed:
    * The name of the currently downloaded channel.
    * The number of posts downloaded from that channel.
    * The content of the downloaded posts (including the link).
    * Any error messages.
* The download process may take a while, depending on the number of channels and posts. Do not close the program window until the process is complete. You can use the "STOP SCRAPING" button if needed.

## 5. Saving Results:

* After the download is complete (or stopped), the application automatically saves the posts to `.txt` file(s).
* The output filename format is: `output_FILENAME-WITH-CHANNELS_YYYY-MM-DD.txt`, where:
    * `FILENAME-WITH-CHANNELS` is the name of the file you selected with the channel list (without the `.txt` extension).
    * `YYYY-MM-DD` is the date from which the posts were downloaded (year-month-day). For range or 'all' modes, multiple files might be created/updated.
* The output file(s) will be created in the same directory where the application's executable (.exe) or Python script is located. Existing `output_*.txt` files will be moved to an `archive` subfolder before a new scrape starts.
* A success, interruption, or error message will appear in a pop-up window.

## 6. Data Analysis with NotebookLM:

* **Key Step:** After downloading the data (the `output_*.txt` files), you can use Google's *NotebookLM* (https://notebooklm.google.com) to efficiently analyze the collected information. NotebookLM works like RAG (Retrieval-Augmented Generation), which means you can "talk" to your data.

   * There are two versions of the notebook. The free version is perfectly sufficient, but no one is stopping you from buying the Plus version.
       > In the NotebookLM version, you can have up to 100 notebooks, and each can contain up to 50 sources. Each source can contain up to half a million words. All users initially get 50 chat queries and can generate 3 audio summaries.
       >
       > If you upgrade to NotebookLM Plus, these limits increase at least 5-fold – to 500 notebooks and 300 sources per notebook. Daily query limits also increase – you will be able to ask up to 500 chat queries and generate 20 audio summaries each day. When sharing a notebook, the source limit does not change: both you and the people you share the notebook with can upload a maximum of 300 sources to it.

![{3BFABF80-1DF0-4C75-B817-88184E8B4240}](https://github.com/user-attachments/assets/5c66fa81-4d65-4c38-b97d-436fc4752983)

* **How to use NotebookLM:**
    1.  Upload the downloaded `.txt` files to NotebookLM as sources.
    2.  NotebookLM will process these files and allow you to ask questions in natural language about their content.
    3.  You can ask for summaries, sentiment analysis, search for specific information, compare content from different channels, identify trends, and even generate new texts based on the downloaded data.
    4.  Use the notebook to ask questions about the uploaded files.

 ![{3BDC503A-D6C4-47C2-87C1-7E3E075F5138}](https://github.com/user-attachments/assets/8f2c9535-5d6a-4776-a7bc-a738fcde6578)


* **Advantages of Analysis in NotebookLM (RAG):**
    * **Context:** NotebookLM analyzes your questions in the *context* of the uploaded data. Answers are based *directly* on information from the files, minimizing the risk of hallucinations (the language model inventing information).
    * **Precision:** You can refer to specific text fragments, making it easier to verify information and track sources. NotebookLM can indicate where a particular answer comes from.
    * **Efficiency:** You don't have to manually search through hundreds of posts. NotebookLM does it for you, saving your time and effort.
    * **Deeper Analysis:** Thanks to the ability to ask questions and generate summaries, you can gain much deeper insights into the data than with traditional analysis. You can discover hidden patterns, connections, and trends that might otherwise be missed.
    * **Interactivity:** NotebookLM allows dynamic interaction with data. You can modify your queries on the fly and get immediate answers.
    * **Security:** NotebookLM, using the uploaded files as its source of information, does not draw information from uncertain sources.

## Additional Notes:

* Ensure you have a stable internet connection while downloading posts.
* For a very large number of channels or posts, downloading may take longer. The 'Download All' option can be particularly time-consuming.
* If an error occurs, check the message content in the "Logs" field and ensure the provided channel name is correct and the channel is publicly accessible via web view.
* The program used the `accless-tg-scraper` library, which worked without using the official Telegram API by scraping the public web preview of channels. https://github.com/Kisspeace/accless-tg-scraper but after some considerations and understanding that updates are nowhere near I had to write my own scrapper from scratch but I still leave link to this repo to point where idea come from.

## REMEMBER THAT THE RESPONSIBILITY FOR VERIFYING SOURCES LIES SOLELY WITH YOU. THE NUMBERS NEXT TO THE TEXT (1) IN NOTEBOOKLM ARE LINKS TO QUOTATIONS USED BY THE LLM. THE OUTPUT FILES FROM THIS APPLICATION CONTAIN THE POST CONTENT AND A DIRECT LINK TO THE ORIGINAL POST (2) ON TELEGRAM FOR VERIFICATION.
![image](https://github.com/user-attachments/assets/3779eb4f-2f3a-4b82-a3e4-1170598bed5f)
