#include "glossary_fast.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <ctype.h>
#include <stdint.h>
#include <limits.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#endif

#define SENTENCE_TIMEOUT_MS 10000.0
#define INITIAL_CAP 64
#define HASH_LOAD_NUM 7
#define HASH_LOAD_DEN 10
#define MAX_SUBSTRING_LEN 64
#define TOP_SENTENCE_LIMIT 2001

typedef struct{const char *ptr;size_t len;} Slice;

typedef struct{
    Slice text;
    size_t line;
    size_t *candidates;
    size_t candidate_count;
    size_t candidate_cap;
    size_t remaining_candidates;
    double score;
} Sentence;

typedef struct{
    char *text;
    size_t len;
    uint64_t hash;
    size_t weight;
    uint32_t type_mask;
    size_t *sentences;
    size_t sentence_count;
    size_t sentence_cap;
} Candidate;

typedef struct{
    Sentence *data;
    size_t count;
    size_t cap;
} SentenceArray;

typedef struct{
    Candidate *data;
    size_t count;
    size_t cap;
    size_t *table;
    size_t table_cap;
} CandidateArray;

static Sentence *g_rank_sentences=NULL;

static double now_ms(void){
#ifdef _WIN32
    static LARGE_INTEGER freq;
    static LONG initialized=0;
    LARGE_INTEGER counter;
    if(!initialized){
        QueryPerformanceFrequency(&freq);
        InterlockedExchange(&initialized,1);
    }
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart*1000.0/(double)freq.QuadPart;
#else
    return (double)clock()*1000.0/(double)CLOCKS_PER_SEC;
#endif
}

static int sentence_timeout(double start_ms){
    return now_ms()-start_ms>=SENTENCE_TIMEOUT_MS;
}

static void *xmalloc(size_t n){
    return malloc(n?n:1);
}

static void *xrealloc(void *p,size_t n){
    return realloc(p,n?n:1);
}

static char *str_dup_len(const char *s,size_t n){
    char *p=(char *)xmalloc(n+1);
    if(!p) return NULL;
    memcpy(p,s,n);
    p[n]=0;
    return p;
}

static int is_utf8_cont(unsigned char c){
    return (c&0xC0)==0x80;
}

static uint32_t utf8_decode(const char *s,size_t len,size_t *used){
    unsigned char c;
    if(!len){
        *used=0;
        return 0;
    }
    c=(unsigned char)s[0];
    if(c<0x80){
        *used=1;
        return c;
    }
    if((c&0xE0)==0xC0&&len>=2&&is_utf8_cont((unsigned char)s[1])){
        *used=2;
        return ((uint32_t)(c&0x1F)<<6)|(uint32_t)(s[1]&0x3F);
    }
    if((c&0xF0)==0xE0&&len>=3&&is_utf8_cont((unsigned char)s[1])&&is_utf8_cont((unsigned char)s[2])){
        *used=3;
        return ((uint32_t)(c&0x0F)<<12)|((uint32_t)(s[1]&0x3F)<<6)|(uint32_t)(s[2]&0x3F);
    }
    if((c&0xF8)==0xF0&&len>=4&&is_utf8_cont((unsigned char)s[1])&&is_utf8_cont((unsigned char)s[2])&&is_utf8_cont((unsigned char)s[3])){
        *used=4;
        return ((uint32_t)(c&0x07)<<18)|((uint32_t)(s[1]&0x3F)<<12)|((uint32_t)(s[2]&0x3F)<<6)|(uint32_t)(s[3]&0x3F);
    }
    *used=1;
    return c;
}

static int is_kanji(uint32_t cp){
    return (cp>=0x3400&&cp<=0x4DBF)||(cp>=0x4E00&&cp<=0x9FFF)||(cp>=0xF900&&cp<=0xFAFF);
}

static int is_hiragana(uint32_t cp){
    return cp>=0x3040&&cp<=0x309F;
}

static int is_katakana(uint32_t cp){
    return (cp>=0x30A0&&cp<=0x30FF)||(cp>=0x31F0&&cp<=0x31FF);
}

static int is_japanese(uint32_t cp){
    return is_kanji(cp)||is_hiragana(cp)||is_katakana(cp)||(cp>=0x3000&&cp<=0x303F);
}

static int is_ascii_upper(unsigned char c){
    return c>='A'&&c<='Z';
}

static int is_ascii_digit(unsigned char c){
    return c>='0'&&c<='9';
}

static size_t cp_count(const char *s,size_t len){
    size_t p=0,n=0,u;
    while(p<len){
        utf8_decode(s+p,len-p,&u);
        if(!u) break;
        p+=u;
        n++;
    }
    return n;
}

static size_t next_pow2(size_t n){
    size_t p=1;
    while(p<n){
        if(p>SIZE_MAX/2) return 0;
        p<<=1;
    }
    return p;
}

static uint64_t hash_bytes(const char *s,size_t len){
    uint64_t h=1469598103934665603ULL;
    size_t i;
    for(i=0;i<len;i++){
        h^=(unsigned char)s[i];
        h*=1099511628211ULL;
    }
    return h;
}

static void sentence_array_init(SentenceArray *a){
    memset(a,0,sizeof(*a));
}

static int sentence_array_push(SentenceArray *a,Slice text,size_t line){
    Sentence *s;
    if(a->count==a->cap){
        size_t nc=a->cap?a->cap*2:INITIAL_CAP;
        Sentence *p=(Sentence *)xrealloc(a->data,nc*sizeof(Sentence));
        if(!p) return 0;
        a->data=p;
        a->cap=nc;
    }
    s=&a->data[a->count++];
    memset(s,0,sizeof(*s));
    s->text=text;
    s->line=line;
    return 1;
}

static void sentence_add_candidate(Sentence *s,size_t id){
    if(s->candidate_count&&s->candidates[s->candidate_count-1]==id) return;
    if(s->candidate_count==s->candidate_cap){
        size_t nc=s->candidate_cap?s->candidate_cap*2:16;
        size_t *p=(size_t *)xrealloc(s->candidates,nc*sizeof(size_t));
        if(!p) return;
        s->candidates=p;
        s->candidate_cap=nc;
    }
    s->candidates[s->candidate_count++]=id;
}

static void candidate_array_init(CandidateArray *a){
    memset(a,0,sizeof(*a));
}

static int candidate_table_init(CandidateArray *a,size_t cap){
    cap=next_pow2(cap<64?64:cap);
    if(!cap) return 0;
    a->table=(size_t *)malloc(cap*sizeof(size_t));
    if(!a->table) return 0;
    memset(a->table,0,cap*sizeof(size_t));
    a->table_cap=cap;
    return 1;
}

static int candidate_table_rebuild(CandidateArray *a,size_t new_cap){
    size_t *table;
    size_t i,pos;
    new_cap=next_pow2(new_cap<64?64:new_cap);
    if(!new_cap) return 0;
    table=(size_t *)malloc(new_cap*sizeof(size_t));
    if(!table) return 0;
    memset(table,0,new_cap*sizeof(size_t));
    for(i=0;i<a->count;i++){
        pos=(size_t)(a->data[i].hash&(new_cap-1));
        while(table[pos]) pos=(pos+1)&(new_cap-1);
        table[pos]=i+1;
    }
    free(a->table);
    a->table=table;
    a->table_cap=new_cap;
    return 1;
}

static size_t candidate_find(const CandidateArray *a,const char *text,size_t len,uint64_t hash){
    size_t pos,idx;
    if(!a->table_cap) return SIZE_MAX;
    pos=(size_t)(hash&(a->table_cap-1));
    for(;;){
        idx=a->table[pos];
        if(!idx) return SIZE_MAX;
        idx--;
        if(a->data[idx].hash==hash&&a->data[idx].len==len&&!memcmp(a->data[idx].text,text,len)) return idx;
        pos=(pos+1)&(a->table_cap-1);
    }
}

static size_t candidate_add(CandidateArray *a,Sentence *s,const char *text,size_t len,size_t weight,uint32_t type_mask){
    uint64_t hash;
    size_t id,pos;
    Candidate *c;

    if(!len) return SIZE_MAX;

    hash=hash_bytes(text,len);
    id=candidate_find(a,text,len,hash);

    if(id!=SIZE_MAX){
        c=&a->data[id];
        c->weight+=weight;
        c->type_mask|=type_mask;

        if(c->sentence_count==c->sentence_cap){
            size_t nc=c->sentence_cap?c->sentence_cap*2:8;
            size_t *p=(size_t *)xrealloc(c->sentences,nc*sizeof(size_t));
            if(!p) return SIZE_MAX;
            c->sentences=p;
            c->sentence_cap=nc;
        }

        sentence_add_candidate(s,id);
        return id;
    }

    if(a->count+1>a->table_cap*HASH_LOAD_NUM/HASH_LOAD_DEN){
        if(!candidate_table_rebuild(a,a->table_cap?a->table_cap*2:64)) return SIZE_MAX;
    }

    if(a->count==a->cap){
        size_t nc=a->cap?a->cap*2:INITIAL_CAP;
        Candidate *p=(Candidate *)xrealloc(a->data,nc*sizeof(Candidate));
        if(!p) return SIZE_MAX;
        a->data=p;
        a->cap=nc;
    }

    id=a->count++;
    c=&a->data[id];
    memset(c,0,sizeof(*c));

    c->text=str_dup_len(text,len);
    if(!c->text){
        a->count--;
        return SIZE_MAX;
    }

    c->len=len;
    c->hash=hash;
    c->weight=weight;
    c->type_mask=type_mask;

    pos=(size_t)(hash&(a->table_cap-1));
    while(a->table[pos]) pos=(pos+1)&(a->table_cap-1);
    a->table[pos]=id+1;

    sentence_add_candidate(s,id);

    return id;
}

static int add_substrings(CandidateArray *candidates,Sentence *s,const char *start,size_t len,size_t min_len,size_t max_len,uint32_t type_mask,double start_ms){
    const char *p=start;
    size_t offsets[MAX_SUBSTRING_LEN+1];
    size_t cp=0,total=0,u,i,end,n;

    offsets[0]=0;

    while(p<start+len&&cp<MAX_SUBSTRING_LEN){
        utf8_decode(p,(size_t)(start+len-p),&u);
        if(!u) break;
        total+=u;
        cp++;
        offsets[cp]=total;
        p+=u;

        if(sentence_timeout(start_ms)) return 0;
    }

    n=cp;
    if(max_len>n) max_len=n;

    for(i=0;i<n;i++){
        size_t first_end=i+min_len;
        if(first_end>n) break;

        for(end=first_end;end<=i+max_len&&end<=n;end++){
            size_t blen=offsets[end]-offsets[i];

            if(blen) candidate_add(candidates,s,start+offsets[i],blen,1,type_mask);

            if(sentence_timeout(start_ms)) return 0;
        }
    }

    return 1;
}

static int process_sentence(Sentence *s,CandidateArray *candidates,double start_ms){
    const char *p=s->text.ptr;
    const char *end=p+s->text.len;

    while(p<end){
        uint32_t cp;
        size_t u;
        const char *run=p;

        cp=utf8_decode(p,(size_t)(end-p),&u);
        if(!u) break;

        if(is_kanji(cp)){
            const char *q=p;
            size_t bytes=0,count=0;

            while(q<end){
                uint32_t x=utf8_decode(q,(size_t)(end-q),&u);
                if(!is_kanji(x)) break;

                q+=u;
                bytes+=u;
                count++;

                if(sentence_timeout(start_ms)) return 0;
            }

            if(count>=2){
                if(!add_substrings(candidates,s,run,bytes,2,8,1,start_ms)) return 0;
            }

            p=q;
        }else{
            p+=u;
        }

        if(sentence_timeout(start_ms)) return 0;
    }

    p=s->text.ptr;

    while(p<end){
        uint32_t cp;
        size_t u;
        const char *run=p;

        cp=utf8_decode(p,(size_t)(end-p),&u);
        if(!u) break;

        if(is_katakana(cp)){
            const char *q=p;
            size_t bytes=0,count=0;

            while(q<end){
                uint32_t x=utf8_decode(q,(size_t)(end-q),&u);
                if(!is_katakana(x)) break;

                q+=u;
                bytes+=u;
                count++;

                if(sentence_timeout(start_ms)) return 0;
            }

            if(count>=2){
                if(!add_substrings(candidates,s,run,bytes,2,8,2,start_ms)) return 0;
            }

            p=q;
        }else{
            p+=u;
        }

        if(sentence_timeout(start_ms)) return 0;
    }

    p=s->text.ptr;

    while(p<end){
        if(is_ascii_upper((unsigned char)*p)){
            const char *q=p;

            while(q<end&&(unsigned char)*q<128&&(isalnum((unsigned char)*q)||*q=='_'||*q=='-')) q++;

            if(q-p>=2) candidate_add(candidates,s,p,(size_t)(q-p),2,4);

            p=q;
        }else{
            p++;
        }

        if(sentence_timeout(start_ms)) return 0;
    }

    p=s->text.ptr;

    while(p<end){
        if(is_ascii_digit((unsigned char)*p)){
            const char *q=p;

            while(q<end&&(is_ascii_digit((unsigned char)*q)||*q=='.'||*q==','||*q=='%'||*q=='-'||*q=='+')) q++;

            const char *r=q;
            size_t jbytes=0;

            while(r<end){
                size_t u;
                uint32_t x=utf8_decode(r,(size_t)(end-r),&u);

                if(!(is_japanese(x)||x==0x30FC)) break;

                r+=u;
                jbytes+=u;

                if(sentence_timeout(start_ms)) return 0;
            }

            if(jbytes>0) candidate_add(candidates,s,p,(size_t)(r-p),2,8);

            p=r;
        }else{
            size_t u;
            utf8_decode(p,(size_t)(end-p),&u);
            if(!u) break;
            p+=u;
        }

        if(sentence_timeout(start_ms)) return 0;
    }

    p=s->text.ptr;

    while(p<end){
        if(*p=='「'||*p=='『'||*p=='“'||*p=='"'){
            char open=*p;
            char close;

            if(open=='「') close='」';
            else if(open=='『') close='』';
            else if(open=='“') close='”';
            else close='"';

            const char *q=p+1;

            while(q<end&&*q!=close){
                q++;
                if(sentence_timeout(start_ms)) return 0;
            }

            if(q<end&&q>p+1){
                size_t n=(size_t)(q-p-1);
                if(n>=2) candidate_add(candidates,s,p+1,n,3,16);
                p=q+1;
            }else{
                p++;
            }
        }else{
            p++;
        }

        if(sentence_timeout(start_ms)) return 0;
    }

    p=s->text.ptr;

    while(p<end){
        uint32_t cp;
        size_t u;

        cp=utf8_decode(p,(size_t)(end-p),&u);
        if(!u) break;

        if(is_japanese(cp)){
            const char *run=p;
            const char *q=p;
            size_t bytes=0,count=0;

            while(q<end){
                uint32_t x=utf8_decode(q,(size_t)(end-q),&u);

                if(!(is_japanese(x)||x==0x30FC)) break;

                q+=u;
                bytes+=u;
                count++;

                if(sentence_timeout(start_ms)) return 0;
            }

            if(count>=2){
                candidate_add(candidates,s,run,bytes,count>=3?2:1,32);

                if(count>=3){
                    if(!add_substrings(candidates,s,run,bytes,2,5,32,start_ms)) return 0;
                }
            }

            p=q;
        }else{
            p+=u;
        }

        if(sentence_timeout(start_ms)) return 0;
    }

    p=s->text.ptr;

    while(p<end){
        size_t u;
        uint32_t cp=utf8_decode(p,(size_t)(end-p),&u);

        if(!u) break;

        if(cp==0x30FB){
            const char *run=p;
            const char *q=p+u;
            size_t count=1;

            while(q<end){
                uint32_t x=utf8_decode(q,(size_t)(end-q),&u);

                if(x==0x30FB){
                    count++;
                    q+=u;
                }else if(is_japanese(x)||is_ascii_upper((unsigned char)*q)||is_ascii_digit((unsigned char)*q)){
                    q+=u;
                }else{
                    break;
                }

                if(sentence_timeout(start_ms)) return 0;
            }

            if(count>=1&&q>run+u) candidate_add(candidates,s,run,(size_t)(q-run),2,64);

            p=q;
        }else{
            p+=u;
        }

        if(sentence_timeout(start_ms)) return 0;
    }

    return 1;
}

static void sentence_array_free(SentenceArray *a){
    size_t i;

    for(i=0;i<a->count;i++) free(a->data[i].candidates);

    free(a->data);
    memset(a,0,sizeof(*a));
}

static void candidate_array_free(CandidateArray *a){
    size_t i;

    for(i=0;i<a->count;i++){
        free(a->data[i].text);
        free(a->data[i].sentences);
    }

    free(a->data);
    free(a->table);
    memset(a,0,sizeof(*a));
}

static int split_sentences(const char *text,size_t len,SentenceArray *out,size_t *max_line){
    size_t p=0;
    size_t start=0;
    size_t line=0;

    while(p<len){
        unsigned char c=(unsigned char)text[p];

        if(c=='\n'||c=='\r'){
            size_t cut=p-start;

            if(cut>0){
                if(!sentence_array_push(out,(Slice){text+start,cut},line)) return 0;
            }

            if(c=='\r'&&p+1<len&&text[p+1]=='\n') p++;

            line++;
            start=p+1;
        }else if(c<128&&(c=='.'||c=='!'||c=='?'||c==';'||c==':')){
            size_t cut=p+1-start;

            if(cut>0){
                if(!sentence_array_push(out,(Slice){text+start,cut},line)) return 0;
            }

            start=p+1;
        }else{
            size_t u;
            uint32_t cp=utf8_decode(text+p,len-p,&u);

            if(cp==0x3002||cp==0xFF01||cp==0xFF1F||cp==0x300D||cp==0x300F||cp==0xFF09){
                p+=u;

                if(p-start>0){
                    if(!sentence_array_push(out,(Slice){text+start,p-start},line)) return 0;
                }

                start=p;
                continue;
            }
        }

        p++;
    }

    if(start<len){
        if(!sentence_array_push(out,(Slice){text+start,len-start},line)) return 0;
    }

    *max_line=line;
    return 1;
}

static double candidate_score(const Candidate *c,size_t sentence_count){
    double spread=sentence_count?((double)c->sentence_count/(double)sentence_count):0.0;
    double len_score=log((double)c->len+1.0);
    double type_bonus=0.0;

    if(c->type_mask&1) type_bonus+=1.5;
    if(c->type_mask&2) type_bonus+=1.2;
    if(c->type_mask&4) type_bonus+=0.8;
    if(c->type_mask&8) type_bonus+=1.0;
    if(c->type_mask&16) type_bonus+=1.3;
    if(c->type_mask&32) type_bonus+=1.4;
    if(c->type_mask&64) type_bonus+=1.0;

    return (double)c->weight*1.5+spread*12.0+len_score+type_bonus;
}

static double sentence_score(const Sentence *s){
    size_t p=0;
    size_t kanji=0;
    size_t kata=0;
    size_t num=0;
    size_t upper=0;
    size_t jp=0;
    size_t total=0;

    while(p<s->text.len){
        size_t u;
        uint32_t cp=utf8_decode(s->text.ptr+p,s->text.len-p,&u);

        if(!u) break;

        total++;

        if(is_kanji(cp)) kanji++;
        if(is_katakana(cp)) kata++;

        if(cp<128){
            if(is_ascii_digit((unsigned char)cp)) num++;
            if(is_ascii_upper((unsigned char)cp)) upper++;
        }

        if(is_japanese(cp)) jp++;

        p+=u;
    }

    if(!total) return -1e9;

    return kanji*2.4+kata*2.0+num*0.8+upper*0.5+(jp>0&&kanji>0?3.0:0.0)+log((double)total+1.0);
}

static int rank_compare(const void *a,const void *b){
    size_t ia=*(const size_t *)a;
    size_t ib=*(const size_t *)b;
    double x=g_rank_sentences[ia].score;
    double y=g_rank_sentences[ib].score;

    if(x<y) return 1;
    if(x>y) return -1;

    return ia>ib?1:ia<ib?-1:0;
}

static int index_compare(const void *a,const void *b){
    size_t x=*(const size_t *)a;
    size_t y=*(const size_t *)b;

    return x>y?1:x<y?-1:0;
}

static char *build_result(SentenceArray *sentences,size_t *selected,size_t selected_count,size_t *out_len){
    size_t i;
    size_t total=0;
    char *out;

    for(i=0;i<selected_count;i++){
        total+=sentences->data[selected[i]].text.len;
        if(i+1<selected_count) total++;
    }

    out=(char *)malloc(total+1);
    if(!out) return NULL;

    {
        size_t pos=0;

        for(i=0;i<selected_count;i++){
            Sentence *s=&sentences->data[selected[i]];

            memcpy(out+pos,s->text.ptr,s->text.len);
            pos+=s->text.len;

            if(i+1<selected_count) out[pos++]='\n';
        }

        out[pos]=0;
        *out_len=pos;
    }

    return out;
}

GLOSSARY_API char *glossary_extract_sample(const char *utf8_text,double percent){
    SentenceArray sentences;
    CandidateArray candidates;
    size_t text_len;
    size_t max_line=0;
    size_t i,j;
    size_t budget;
    size_t *ranked=NULL;
    size_t *selected=NULL;
    unsigned char *selected_flags=NULL;
    unsigned char *selected_lines=NULL;
    unsigned char *used_candidates=NULL;
    size_t selected_count=0;
    size_t used_bytes=0;
    char *result=NULL;
    size_t result_len=0;

    sentence_array_init(&sentences);
    candidate_array_init(&candidates);

    if(!utf8_text) return NULL;

    text_len=strlen(utf8_text);

    if(percent<0.1||percent>100.0) percent*=10.0;

    if(percent<0.1) percent=0.1;
    if(percent>100.0) percent=100.0;

    budget=(size_t)((double)text_len*(percent/100.0));

    if(budget==0) budget=1;

    if(percent>=100.0){
        return str_dup_len(utf8_text,text_len);
    }

    if(!split_sentences(utf8_text,text_len,&sentences,&max_line)){
        sentence_array_free(&sentences);
        return NULL;
    }

    if(!candidate_table_init(&candidates,64)){
        sentence_array_free(&sentences);
        return NULL;
    }

    for(i=0;i<sentences.count;i++){
        Sentence *s=&sentences.data[i];
        CandidateArray temp;
        double sentence_start=now_ms();
        size_t j2;

        candidate_array_init(&temp);

        if(!candidate_table_init(&temp,64)) continue;

        if(!process_sentence(s,&temp,sentence_start)){
            candidate_array_free(&temp);
            continue;
        }

        if(sentence_timeout(sentence_start)){
            candidate_array_free(&temp);
            continue;
        }

        for(j2=0;j2<temp.count;j2++){
            Candidate *tc=&temp.data[j2];

            candidate_add(
                &candidates,
                s,
                tc->text,
                tc->len,
                tc->weight,
                tc->type_mask
            );
        }

        candidate_array_free(&temp);
    }

    for(i=0;i<candidates.count;i++){
        candidates.data[i].weight=(size_t)fmax(
            1.0,
            candidate_score(&candidates.data[i],sentences.count)
        );
    }

    for(i=0;i<sentences.count;i++){
        sentences.data[i].score=sentence_score(&sentences.data[i]);
        sentences.data[i].remaining_candidates=sentences.data[i].candidate_count;
    }

    for(i=0;i<candidates.count;i++){
        Candidate *c=&candidates.data[i];

        for(j=0;j<c->sentence_count;j++){
            size_t sid=c->sentences[j];

            if(sid<sentences.count){
                sentences.data[sid].remaining_candidates++;
            }
        }
    }

    for(i=0;i<sentences.count;i++){
        if(sentences.data[i].candidate_count){
            sentences.data[i].remaining_candidates-=sentences.data[i].candidate_count;
        }
    }

    if(sentences.count){
        ranked=(size_t *)malloc(sentences.count*sizeof(size_t));
        selected=(size_t *)malloc(sentences.count*sizeof(size_t));
    }

    selected_flags=(unsigned char *)calloc(
        sentences.count?sentences.count:1,
        sizeof(unsigned char)
    );

    selected_lines=(unsigned char *)calloc(
        max_line+3,
        sizeof(unsigned char)
    );

    used_candidates=(unsigned char *)calloc(
        candidates.count?candidates.count:1,
        sizeof(unsigned char)
    );

    if(!ranked||!selected||!selected_flags||!selected_lines||!used_candidates){
        free(ranked);
        free(selected);
        free(selected_flags);
        free(selected_lines);
        free(used_candidates);
        candidate_array_free(&candidates);
        sentence_array_free(&sentences);
        return NULL;
    }

    for(i=0;i<sentences.count;i++) ranked[i]=i;

    g_rank_sentences=sentences.data;
    qsort(ranked,sentences.count,sizeof(size_t),rank_compare);
    g_rank_sentences=NULL;

    while(used_bytes<budget&&selected_count<sentences.count){
        size_t limit=sentences.count<TOP_SENTENCE_LIMIT?sentences.count:TOP_SENTENCE_LIMIT;
        size_t best=SIZE_MAX;
        double best_score=-1e100;

        for(i=0;i<limit;i++){
            size_t sid=ranked[i];
            Sentence *s=&sentences.data[sid];
            double score;
            int nearby=0;

            if(selected_flags[sid]) continue;

            if(used_bytes+s->text.len>budget) continue;

            if(s->line>=2&&selected_lines[s->line-2]) nearby=1;
            if(selected_lines[s->line-1]) nearby=1;
            if(selected_lines[s->line]) nearby=1;
            if(selected_lines[s->line+1]) nearby=1;
            if(selected_lines[s->line+2]) nearby=1;

            score=s->score+(double)s->remaining_candidates*2.5;

            if(nearby) score-=5.0;

            if(score>best_score){
                best_score=score;
                best=sid;
            }
        }

        if(best==SIZE_MAX) break;

        selected_flags[best]=1;
        selected[selected_count++]=best;
        used_bytes+=sentences.data[best].text.len;

        if(sentences.data[best].line<=max_line+2){
            selected_lines[sentences.data[best].line]=1;
        }

        for(j=0;j<sentences.data[best].candidate_count;j++){
            size_t cid=sentences.data[best].candidates[j];
            Candidate *c;
            size_t k;

            if(cid>=candidates.count) continue;
            if(used_candidates[cid]) continue;

            used_candidates[cid]=1;
            c=&candidates.data[cid];

            for(k=0;k<c->sentence_count;k++){
                size_t sid=c->sentences[k];

                if(sid<sentences.count&&sentences.data[sid].remaining_candidates>0){
                    sentences.data[sid].remaining_candidates--;
                }
            }
        }
    }

    qsort(selected,selected_count,sizeof(size_t),index_compare);

    result=build_result(
        &sentences,
        selected,
        selected_count,
        &result_len
    );

    free(ranked);
    free(selected);
    free(selected_flags);
    free(selected_lines);
    free(used_candidates);

    candidate_array_free(&candidates);
    sentence_array_free(&sentences);

    return result;
}

GLOSSARY_API void glossary_free(char *ptr){
    free(ptr);
}