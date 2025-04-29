from typing import List
from ..core.config import settings
from sklearn.metrics.pairwise import cosine_similarity
import torch
#from sentence_transformers import SentenceTransformer → problems wit transfoermrs 4.38.2 that is needed fot OCR analysis
# The commended function is for using sentenceTransformers
import torch
import torch.nn.functional as F
from .standardar_chuncker import chunk_document
#from app.services.llm import get_client
#from transformers import AutoModel, AutoTokenizer
from google import genai
from google.genai import types

#model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")



"""
model_name = "sentence-transformers/all-MiniLM-L6-v2"
model = AutoModel.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
"""
llm_client = genai.Client(api_key=settings.GEMINI_API_KEY)

def chunk_document_cosine(text:str)->List[str]:

    chunks=get_initial_chunks(text)
    if len(chunks)>=1:
        distances, chunks=_cosine_distance(chunks)
        indices_above_trheshold=_indices_above_treshold_distance(distances)
        chunks=_group_chunks(indices_above_trheshold, chunks)
        chunks=_remove_artifacts(chunks)
    return chunks

def _remove_artifacts(chunks):
    # remove artifacts
    for sentence in chunks:
        # Remove index and sentence field in the list of dictionary
        sentence.pop('index', None)
        sentence.pop('sentence')
    return chunks



def get_initial_chunks(text:str):
    chunks=chunk_document(text)
    chunks = [{'sentence': x, 'index' : i} for i, x in enumerate(chunks)]
    # the second argument indicates the number of sentences to combine before and after the current sentence
    chunks = _combine_sentences(chunks, 1)
    # emnedding
    chunks=_do_embedding(chunks)
    return chunks

def _group_chunks(indices, sentences):
    # initialize the start index
    start_index = 0
    # create a list to hold the grouped sentences
    final_chunks = []
    # iterate through the breakpoints to slice the sentences
    for index in indices:
        # the end index is the current breakpoint
        end_index = index
        # slice the sentence_dicts from the current start index to the end index
        group = sentences[start_index:end_index + 1]
        combined_text = ' '.join([repr(d['sentence']) for d in group])
        final_chunks.extend(_check_len([combined_text]))
        start_index = index + 1
    # the last group, if any sentences remain
    if start_index < len(sentences):
        combined_text = ' '.join([repr(d['sentence']) for d in sentences[start_index:]])
        final_chunks.extend(_check_len([combined_text]))
    return final_chunks

def _check_len(chunk):
    # token count
    token_count=llm_client.models.count_tokens(model=settings.GEMINI_MODEL_NAME, contents=chunk)
    #tokenizer=model.tokenizer
    #tokens = tokenizer(chunk, return_tensors="pt")
    #token_count = tokens.input_ids.shape[1]
    # chek if the amount of token id above the limit
    if token_count.total_tokens > settings.MAX_TOKEN_PER_CHUNK_GROUPED:
        docs_split=chunk_document(chunk)
        # get new embeddings for the new chunks
        return _get_new_chunk(len(docs_split), docs_split)
    else:
        #st.write("Sotto i 1024")
        return _get_new_chunk(1, chunk)

def _get_new_chunk(leng, chunks):
    splitted_chunks = []
    # get strings from documents
    string_text = [chunks for i in range(leng)]
    chunks_edit = [{'sentence': x, 'index' : i} for i, x in enumerate(string_text)]
    chunks_edit = [{'sentence': f"{x['sentence']}", 'index': x['index']} for x in chunks_edit]
    # get sentence and combined_sentence
    for i in range(len(chunks_edit)):
        combined_sentence = chunks_edit[i]['sentence']
        chunks_edit[i]['section'] = combined_sentence
    # get new embeddings for the new chunks
    chunks_edit=_do_embedding(chunks_edit)
    # add the new chunks to the list
    splitted_chunks.extend(chunks_edit)
    return splitted_chunks


def _indices_above_treshold_distance(distances, distance=0.95):
    # identify the outlier
    # higher distance --> less chunks
    # lower distance --> more chunks
    # Indexes of the chunks with cosine distance above treshold
    indices_above_thresh=[]
    for i, x in enumerate(distances):
        if (1-x)<(distance):
            indices_above_thresh.append(i)
    return indices_above_thresh

def _cosine_distance(chunks):
    distances = []
    for i in range(len(chunks) - 1):
        embedding_current = chunks[i]['embedding']
        embedding_next = chunks[i + 1]['embedding']
        # calculate cosine similarity
        similarity = cosine_similarity([embedding_current], [embedding_next])[0][0]
        # convert to cosine distance
        distance = 1 - similarity
        # append cosine distance to the list
        distances.append(distance)
        # store distance in the dictionary
        chunks[i]['distance_to_next'] = distance
    return distances, chunks

def _do_embedding(chunks):
    embeddings = []
    for i, chunk in enumerate(chunks):
        result = llm_client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=chunk['section'],
            config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
        )
        embedding = result.embeddings[0].values
        #embedding = model.encode(chunk['section'], show_progress_bar=False)
        embeddings.append(embedding)
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
    return chunks

#buffer size: number of sentence before and after the current one to be joined
def _combine_sentences(chunks:str, buffer_size):
    for i in range(len(chunks)):
        # create a string for the joined sentences
        combined_sentence = ''
        # add sentences before the current one, based on the buffer size.
        for j in range(i - buffer_size, i):
            # check if the index j is not negative (avoid problem for the first sentence)
            if j >= 0:
                combined_sentence += chunks[j]['sentence'] + ' '
        # add the current sentence
        combined_sentence += chunks[i]['sentence']

        # add sentences after the current one, based on the buffer size
        for j in range(i + 1, i + 1 + buffer_size):
            # check if the index j is within the range of the sentences list
            if j < len(chunks):
                combined_sentence += ' ' + chunks[j]['sentence']
        # store the combined sentence in the current sentence dict
        chunks[i]['section'] = combined_sentence
    return chunks

