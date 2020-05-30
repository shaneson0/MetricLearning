from os.path import join
import codecs
import math
from collections import defaultdict as dd
from global_.embedding import EmbeddingModel
from datetime import datetime
from utils.cache import LMDBClient
from utils import data_utils
from utils import feature_utils
from utils import settings
import json

start_time = datetime.now()

def dump_author_social_relation_to_file():
    pubs_dict = data_utils.load_json(settings.GLOBAL_DATA_DIR, 'pubs_raw.json')
    wf = codecs.open(join(settings.GLOBAL_DATA_DIR, 'author_social.txt'), 'w', encoding='utf-8')

    Authors = []
    for i, pid in enumerate(pubs_dict):
        paper = pubs_dict[pid]
        if "title" not in paper or "authors" not in paper:
            continue
        if len(paper["authors"]) > 100:
            continue
        coauthors = [str(x['name']) + ':' + str(x.get('org', 'null')) for x in paper["authors"]]
        # print('pid: ', pid, ,'coauthors: ', coauthors)
        print('pid: ', pid)
        Authors = Authors + coauthors
    Authors = set(Authors)

    Author2Id = { author:idx for idx, author in enumerate(Authors)}
    Id2Author = { idx:author for idx, author in enumerate(Authors)}
    # print(Authors)
    print(Author2Id)

    for i, pid in enumerate(pubs_dict):
        paper = pubs_dict[pid]
        if "title" not in paper or "authors" not in paper:
            continue
        if len(paper["authors"]) > 30:
            print(i, pid, len(paper["authors"]))
        if len(paper["authors"]) > 100:
            continue

        n_authors = len(paper.get('authors', []))
        for j in range(n_authors):
            author_social_relatoins = feature_utils.extract_author_social(paper, Author2Id)
            aid = '{}-{}'.format(pid, j)
            wf.write(aid + '\t' + author_social_relatoins + '\n')
    wf.close()
    with open('./data/global_/Author2Id.json', 'w') as fp:
        json.dump(Author2Id, fp)
        fp.close()
    with open('./data/global_/Id2Author.json', 'w') as fp:
        json.dump(Id2Author, fp)
        fp.close()

def dump_author_features_to_file():
    """
    generate author features by raw publication data and dump to files
    author features are defined by his/her paper attributes excluding the author's name
    """
    pubs_dict = data_utils.load_json(settings.GLOBAL_DATA_DIR, 'pubs_raw.json')
    print('n_papers', len(pubs_dict))
    wf = codecs.open(join(settings.GLOBAL_DATA_DIR, 'author_features.txt'), 'w', encoding='utf-8')
    for i, pid in enumerate(pubs_dict):
        if i % 1000 == 0:
            print(i, datetime.now()-start_time)
        paper = pubs_dict[pid]
        if "title" not in paper or "authors" not in paper:
            continue
        if len(paper["authors"]) > 30:
            print(i, pid, len(paper["authors"]))
        if len(paper["authors"]) > 100:
            continue
        n_authors = len(paper.get('authors', []))
        for j in range(n_authors):
            author_feature = feature_utils.extract_author_features(paper, j)
            aid = '{}-{}'.format(pid, j)
            wf.write(aid + '\t' + ' '.join(author_feature) + '\n')
    wf.close()




def dump_author_features_to_cache():
    """
    dump author features to lmdb
    """
    LMDB_NAME = 'pub_authors.feature'
    lc = LMDBClient(LMDB_NAME)
    with codecs.open(join(settings.GLOBAL_DATA_DIR, 'author_features.txt'), 'r', encoding='utf-8') as rf:
        for i, line in enumerate(rf):
            if i % 1000 == 0:
                print('line', i)
            items = line.rstrip().split('\t')
            pid_order = items[0]
            author_features = items[1].split()
            lc.set(pid_order, author_features)


def cal_feature_idf():
    """
    calculate word IDF (Inverse document frequency) using publication data
    """
    feature_dir = join(settings.DATA_DIR, 'global_')
    counter = dd(int)
    cnt = 0
    LMDB_NAME = 'pub_authors.feature'
    lc = LMDBClient(LMDB_NAME)
    author_cnt = 0
    with lc.db.begin() as txn:
        for k in txn.cursor():
            features = data_utils.deserialize_embedding(k[1])
            if author_cnt % 10000 == 0:
                print(author_cnt, features[0], counter.get(features[0]))
            author_cnt += 1
            for f in features:
                cnt += 1
                counter[f] += 1
    idf = {}
    for k in counter:
        idf[k] = math.log(cnt / counter[k])
    data_utils.dump_data(dict(idf), feature_dir, "feature_idf.pkl")


def dump_author_embs():
    """
    dump author embedding to lmdb
    author embedding is calculated by weighted-average of word vectors with IDF
    """
    emb_model = EmbeddingModel.Instance()
    idf = data_utils.load_data(settings.GLOBAL_DATA_DIR, 'feature_idf.pkl')
    print('idf loaded')
    LMDB_NAME_FEATURE = 'pub_authors.feature'
    lc_feature = LMDBClient(LMDB_NAME_FEATURE)
    LMDB_NAME_EMB = "author_100.emb.weighted"
    lc_emb = LMDBClient(LMDB_NAME_EMB)
    cnt = 0
    with lc_feature.db.begin() as txn:
        for k in txn.cursor():
            if cnt % 1000 == 0:
                print('cnt', cnt, datetime.now()-start_time)
            cnt += 1
            pid_order = k[0].decode('utf-8')
            features = data_utils.deserialize_embedding(k[1])
            cur_emb = emb_model.project_embedding(features, idf)
            if cur_emb is not None:
                lc_emb.set(pid_order, cur_emb)


if __name__ == '__main__':
    """
    some pre-processing
    """
    print ("pass0")
    dump_author_features_to_file()
    print ("pass1")
    dump_author_features_to_cache()
    print ("pass2")
    emb_model = EmbeddingModel.Instance()
    emb_model.train('aminer')  # training word embedding model
    cal_feature_idf()
    print ("pass3")
    dump_author_embs()
    # print('done', datetime.now()-start_time)

    # Author social relation
    print ("pass4")
    dump_author_social_relation_to_file()


