#include "glossary_fast.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <ctype.h>
#include <stdint.h>

#ifndef SIZE_MAX
#define SIZE_MAX ((size_t)-1)
#endif

typedef struct { const char *start; size_t len; } Slice;
typedef struct {
    char *text; size_t len, line; double score; int selected;
    size_t *candidates, candidate_count, candidate_capacity;
} Sentence;
typedef struct {
    char *text; size_t len; double weight; unsigned int type_mask;
    size_t *sentences, sentence_count, sentence_capacity;
    uint64_t hash;
} Candidate;
typedef struct { Sentence *data; size_t count, capacity; } SentenceArray;
typedef struct {
    Candidate *data; size_t count, capacity;
    size_t *hash_table, hash_capacity;
} CandidateArray;

static void *xmalloc(size_t n){ return malloc(n ? n : 1); }
static void *xrealloc(void *p,size_t n){ return realloc(p,n ? n : 1); }

static char *str_dup_len(const char *s,size_t len){
    char *p=(char*)xmalloc(len+1);
    if(!p)return NULL;
    memcpy(p,s,len); p[len]=0; return p;
}

static int is_utf8_cont(unsigned char c){ return (c&0xC0)==0x80; }

static unsigned int utf8_decode(const char *s,size_t len,size_t *used){
    unsigned char c;
    if(!len){*used=0;return 0;}
    c=(unsigned char)s[0];
    if(c<0x80){*used=1;return c;}
    if((c&0xE0)==0xC0&&len>=2&&is_utf8_cont((unsigned char)s[1])){
        *used=2;return ((unsigned)(c&31)<<6)|(s[1]&63);
    }
    if((c&0xF0)==0xE0&&len>=3&&is_utf8_cont((unsigned char)s[1])&&is_utf8_cont((unsigned char)s[2])){
        *used=3;return ((unsigned)(c&15)<<12)|((s[1]&63)<<6)|(s[2]&63);
    }
    if((c&0xF8)==0xF0&&len>=4&&is_utf8_cont((unsigned char)s[1])&&is_utf8_cont((unsigned char)s[2])&&is_utf8_cont((unsigned char)s[3])){
        *used=4;return ((unsigned)(c&7)<<18)|((s[1]&63)<<12)|((s[2]&63)<<6)|(s[3]&63);
    }
    *used=1;return 0xFFFD;
}

static int is_kanji(unsigned int c){
    return (c>=0x3400&&c<=0x4DBF)||(c>=0x4E00&&c<=0x9FFF)||
           c==0x3005||c==0x3006||c==0x3007||c==0x30F6;
}
static int is_hiragana(unsigned int c){ return c>=0x3040&&c<=0x309F; }
static int is_katakana(unsigned int c){ return c>=0x30A0&&c<=0x30FF; }
static int is_japanese(unsigned int c){ return is_kanji(c)||is_hiragana(c)||is_katakana(c); }
static int is_ascii_alnum(unsigned int c){ return c<128&&isalnum((unsigned char)c); }
static int is_ascii_upper(unsigned int c){ return c>='A'&&c<='Z'; }
static int is_space_cp(unsigned int c){ return c==' '||c=='\t'||c=='\r'||c=='\n'; }

static size_t cp_count(const char *s,size_t len){
    size_t p=0,n=0,u;
    while(p<len){utf8_decode(s+p,len-p,&u);if(!u)break;p+=u;n++;}
    return n;
}

static void sentence_array_init(SentenceArray *a){
    memset(a,0,sizeof(*a));
}
static int sentence_add_candidate(Sentence *s,size_t id){
    if(s->candidate_count&&s->candidates[s->candidate_count-1]==id)return 1;
    if(s->candidate_count==s->candidate_capacity){
        size_t nc=s->candidate_capacity?s->candidate_capacity*2:32;
        size_t *p=(size_t*)xrealloc(s->candidates,nc*sizeof(size_t));
        if(!p)return 0;
        s->candidates=p;s->candidate_capacity=nc;
    }
    s->candidates[s->candidate_count++]=id;
    return 1;
}
static int sentence_array_push(SentenceArray *a,const char *s,size_t len,size_t line){
    if(a->count==a->capacity){
        size_t nc=a->capacity?a->capacity*2:256;
        Sentence *p=(Sentence*)xrealloc(a->data,nc*sizeof(Sentence));
        if(!p)return 0;
        a->data=p;a->capacity=nc;
    }
    Sentence *x=&a->data[a->count];
    memset(x,0,sizeof(*x));
    x->text=str_dup_len(s,len);
    if(!x->text)return 0;
    x->len=len;x->line=line;
    a->count++;
    return 1;
}
static void sentence_array_free(SentenceArray *a){
    size_t i;
    for(i=0;i<a->count;i++){free(a->data[i].text);free(a->data[i].candidates);}
    free(a->data);
}

static uint64_t hash_bytes(const char *s,size_t len){
    uint64_t h=1469598103934665603ULL;
    size_t i;
    for(i=0;i<len;i++){h^=(unsigned char)s[i];h*=1099511628211ULL;}
    return h;
}
static size_t next_pow2(size_t n){
    size_t p=1;
    while(p<n)p<<=1;
    return p;
}
static void candidate_array_init(CandidateArray *a){memset(a,0,sizeof(*a));}

static int candidate_hash_init(CandidateArray *a,size_t expected){
    size_t cap=next_pow2(expected*2+1024),i;
    a->hash_table=(size_t*)malloc(cap*sizeof(size_t));
    if(!a->hash_table)return 0;
    a->hash_capacity=cap;
    for(i=0;i<cap;i++)a->hash_table[i]=SIZE_MAX;
    return 1;
}
static int candidate_hash_rebuild(CandidateArray *a){
    size_t cap=next_pow2(a->count*2+1024),i;
    size_t *t;
    if(cap<=a->hash_capacity)return 1;
    t=(size_t*)malloc(cap*sizeof(size_t));
    if(!t)return 0;
    for(i=0;i<cap;i++)t[i]=SIZE_MAX;
    for(i=0;i<a->count;i++){
        size_t p=(size_t)(a->data[i].hash&(cap-1));
        while(t[p]!=SIZE_MAX)p=(p+1)&(cap-1);
        t[p]=i;
    }
    free(a->hash_table);a->hash_table=t;a->hash_capacity=cap;
    return 1;
}
static int candidate_find(CandidateArray *a,const char *text,size_t len,uint64_t hash){
    size_t p,id;
    if(!a->hash_table)return -1;
    p=(size_t)(hash&(a->hash_capacity-1));
    while((id=a->hash_table[p])!=SIZE_MAX){
        Candidate *c=&a->data[id];
        if(c->hash==hash&&c->len==len&&!memcmp(c->text,text,len))return (int)id;
        p=(p+1)&(a->hash_capacity-1);
    }
    return -1;
}
static int candidate_add(CandidateArray *a,SentenceArray *sa,const char *text,size_t len,size_t sentence,double weight,unsigned int type){
    uint64_t hash;
    int index;
    Candidate *c;
    if(len<2||len>150)return 1;
    hash=hash_bytes(text,len);
    index=candidate_find(a,text,len,hash);
    if(index<0){
        if(a->count+1>a->hash_capacity*7/10)
            if(!candidate_hash_rebuild(a))return 0;
        if(a->count==a->capacity){
            size_t nc=a->capacity?a->capacity*2:4096;
            Candidate *p=(Candidate*)xrealloc(a->data,nc*sizeof(Candidate));
            if(!p)return 0;
            a->data=p;a->capacity=nc;
        }
        index=(int)a->count++;
        c=&a->data[index];
        memset(c,0,sizeof(*c));
        c->text=str_dup_len(text,len);
        if(!c->text)return 0;
        c->len=len;c->hash=hash;
        {
            size_t p=(size_t)(hash&(a->hash_capacity-1));
            while(a->hash_table[p]!=SIZE_MAX)p=(p+1)&(a->hash_capacity-1);
            a->hash_table[p]=(size_t)index;
        }
    }
    c=&a->data[index];
    c->weight+=weight;c->type_mask|=type;
    if(c->sentence_count==0||c->sentences[c->sentence_count-1]!=sentence){
        if(c->sentence_count==c->sentence_capacity){
            size_t nc=c->sentence_capacity?c->sentence_capacity*2:8;
            size_t *p=(size_t*)xrealloc(c->sentences,nc*sizeof(size_t));
            if(!p)return 0;
            c->sentences=p;c->sentence_capacity=nc;
        }
        c->sentences[c->sentence_count++]=sentence;
        if(!sentence_add_candidate(&sa->data[sentence],(size_t)index))return 0;
    }
    return 1;
}
static void candidate_array_free(CandidateArray *a){
    size_t i;
    for(i=0;i<a->count;i++){free(a->data[i].text);free(a->data[i].sentences);}
    free(a->data);free(a->hash_table);
}

static void add_substrings(CandidateArray *ca,SentenceArray *sa,const char *s,size_t len,size_t sentence,int min_n,int max_n,double weight,unsigned int type){
    Slice chars[64];
    size_t count=0,p=0,i,total,j;
    int n;
    while(p<len&&count<64){
        size_t u;utf8_decode(s+p,len-p,&u);if(!u)break;
        chars[count].start=s+p;chars[count].len=u;count++;p+=u;
    }
    for(n=min_n;n<=max_n&&n<=(int)count;n++){
        for(i=0;i+(size_t)n<=count;i++){
            total=0;
            for(j=0;j<(size_t)n;j++)total+=chars[i+j].len;
            if(!candidate_add(ca,sa,chars[i].start,total,sentence,weight,type))return;
        }
    }
}

static int find_suffix(const char *text,size_t len,const char **suffixes,size_t count,size_t *slen){
    size_t i;
    for(i=0;i<count;i++){
        size_t n=strlen(suffixes[i]);
        if(len>=n&&!memcmp(text+len-n,suffixes[i],n)){*slen=n;return 1;}
    }
    return 0;
}

static int process_sentence(Sentence *s,size_t si,CandidateArray *ca,SentenceArray *sa){
    const char *text=s->text;size_t len=s->len,p=0;
    static const char *title[]={"王","女王","皇帝","皇女","王子","王女","姫","公爵","侯爵","伯爵","子爵","男爵","騎士","団長","隊長","将軍","司令","魔王","勇者","聖女","賢者","神官","巫女","剣士","魔術師","魔導師","冒険者","商人","貴族","兵士"};
    static const char *place[]={"国","王国","帝国","共和国","領","城","街","町","村","都市","学院","学園","教会","神殿","寺院","騎士団","兵団","軍団","ギルド","パーティー","組織"};
    static const char *item[]={"剣","刀","槍","弓","杖","盾","鎧","兜","指輪","首飾り","魔法","術","技","スキル","武器","防具","薬","秘薬","宝","神器","聖具","魔具"};
    static const char *race[]={"族","種","人","獣","竜","妖精","精霊","悪魔","天使","吸血鬼","魔族","人族"};
    const char **groups[]={title,place,item,race};
    size_t counts[]={sizeof(title)/sizeof(title[0]),sizeof(place)/sizeof(place[0]),sizeof(item)/sizeof(item[0]),sizeof(race)/sizeof(race[0])};

    while(p<len){
        size_t used;unsigned int c=utf8_decode(text+p,len-p,&used);
        if(!used)break;
        if(is_kanji(c)){
            size_t st=p,q=p,n=0;
            while(q<len){
                size_t u;unsigned int x=utf8_decode(text+q,len-q,&u);
                if(!u||!is_kanji(x))break;
                q+=u;if(++n>=20)break;
            }
            if(n>=2){
                if(!candidate_add(ca,sa,text+st,q-st,si,1.0,1))return 0;
                add_substrings(ca,sa,text+st,q-st,si,2,7,.7,2);
            }
            p=q;continue;
        }
        if(is_katakana(c)){
            size_t st=p,q=p,n=0;
            while(q<len){
                size_t u;unsigned int x=utf8_decode(text+q,len-q,&u);
                if(!u||!is_katakana(x))break;
                q+=u;if(++n>=30)break;
            }
            if(n>=2){
                if(!candidate_add(ca,sa,text+st,q-st,si,1.5,4))return 0;
                if(n>=4)add_substrings(ca,sa,text+st,q-st,si,3,11,.5,8);
            }
            p=q;continue;
        }
        if(is_ascii_upper(c)){
            size_t st=p,q=p;
            while(q<len){
                unsigned char x=(unsigned char)text[q];
                if(!(x<128&&(isalnum(x)||x=='_'||x=='-')))break;
                q++;
            }
            if(q-st>=3&&!candidate_add(ca,sa,text+st,q-st,si,2.0,16))return 0;
            p=q;continue;
        }
        if(c<128&&isdigit((unsigned char)c)){
            size_t st=p,q=p;
            while(q<len){
                unsigned char x=(unsigned char)text[q];
                if(x<128&&(isdigit(x)||x=='.'))q++;else break;
            }
            {
                size_t u;unsigned int next=utf8_decode(text+q,len-q,&u);
                if(u&&is_japanese(next)){
                    size_t end=q;
                    while(end<len){
                        unsigned int z;size_t v;
                        z=utf8_decode(text+end,len-end,&v);
                        if(!v||!is_japanese(z))break;
                        end+=v;if(end-q>60)break;
                    }
                    if(!candidate_add(ca,sa,text+st,end-st,si,1.5,32))return 0;
                }
            }
            p=q;continue;
        }
        p+=used;
    }

    {
        size_t i=0;
        while(i<len){
            size_t u;unsigned int cp=utf8_decode(text+i,len-i,&u);
            if(!u)break;
            if(cp==0x300C||cp==0x300E||cp==0x3010||cp==0x3008||cp==0x300A||cp==0xFF08){
                unsigned int close=cp==0x300C?0x300D:cp==0x300E?0x300F:cp==0x3010?0x3011:cp==0x3008?0x3009:cp==0x300A?0x300B:0xFF09;
                size_t st=i+u,q=st;
                while(q<len){
                    size_t v;unsigned int x=utf8_decode(text+q,len-q,&v);
                    if(!v)break;
                    if(x==close){
                        if(q>st&&q-st<=150&&!candidate_add(ca,sa,text+st,q-st,si,3.5,64))return 0;
                        i=q+v;break;
                    }
                    q+=v;if(q-st>180)break;
                }
                if(q>=len)i+=u;
                continue;
            }
            i+=u;
        }
    }

    {
        size_t i;
        for(i=0;i<len;){
            size_t u;unsigned int cp=utf8_decode(text+i,len-i,&u);
            if(!u)break;
            if(is_japanese(cp)){
                size_t st=i,q=i,n=0;
                while(q<len){
                    size_t v;unsigned int x=utf8_decode(text+q,len-q,&v);
                    if(!v||!is_japanese(x))break;
                    q+=v;if(++n>=20)break;
                }
                if(n>=2){
                    size_t g;
                    for(g=0;g<4;g++){
                        size_t sl=0;
                        if(find_suffix(text+st,q-st,groups[g],counts[g],&sl)){
                            double w=g==0?3.0:g==1?2.8:g==2?3.0:2.5;
                            unsigned int type=g==0?128:g==1?256:g==2?512:1024;
                            if(!candidate_add(ca,sa,text+st,q-st,si,w,type))return 0;
                        }
                    }
                }
                i=q;
            }else i+=u;
        }
    }

    {
        size_t i;
        for(i=0;i<len;i++){
            if((unsigned char)text[i]==0xE3){
                size_t u;unsigned int cp=utf8_decode(text+i,len-i,&u);
                if(cp==0x30FB){
                    size_t left=i,right=i+u;
                    while(left){
                        size_t back=left;
                        while(back&&is_utf8_cont((unsigned char)text[back-1]))back--;
                        if(!back){left=0;break;}
                        {
                            size_t v;unsigned int x=utf8_decode(text+back,left-back,&v);
                            if(!is_japanese(x)&&!is_ascii_alnum(x))break;
                            left=back;
                        }
                    }
                    while(right<len){
                        size_t v;unsigned int x=utf8_decode(text+right,len-right,&v);
                        if(!v||(!is_japanese(x)&&!is_ascii_alnum(x)))break;
                        right+=v;if(right-left>80)break;
                    }
                    if(i>left&&right>i+u&&!candidate_add(ca,sa,text+left,right-left,si,2.5,2048))return 0;
                }
            }
        }
    }
    return 1;
}

static int rank_compare(const void *a,const void *b){
    const Sentence *sa=*(const Sentence**)a,*sb=*(const Sentence**)b;
    if(sa->score<sb->score)return 1;
    if(sa->score>sb->score)return -1;
    return sa->line>sb->line?1:sa->line<sb->line?-1:0;
}
static int index_compare(const void *a,const void *b){
    size_t x=*(const size_t*)a,y=*(const size_t*)b;
    return x>y?1:x<y?-1:0;
}

static char *build_result(SentenceArray *sa,size_t *selected,size_t count,size_t budget){
    size_t i,total=0,pos=0;
    char *r;
    for(i=0;i<count;i++){
        size_t n=sa->data[selected[i]].len;
        if(total+n>budget)break;
        if(i)total++;
        total+=n;
    }
    if(total>budget)total=budget;
    r=(char*)xmalloc(total+1);
    if(!r)return NULL;
    for(i=0;i<count;i++){
        Sentence *s=&sa->data[selected[i]];
        if(pos+s->len>budget)break;
        if(pos){if(pos>=total)break;r[pos++]='\n';}
        if(pos+s->len>total)break;
        memcpy(r+pos,s->text,s->len);pos+=s->len;
    }
    r[pos]=0;return r;
}

GLOSSARY_API char *glossary_extract_sample(const char *utf8_text,double percent){
    SentenceArray sentences;
    CandidateArray candidates;
    size_t text_len,budget,p=0,start=0,line=0,i;
    Sentence **ranked=NULL;
    size_t *selected=NULL;
    size_t selected_count=0;
    unsigned char *selected_flags=NULL,*used_candidate=NULL;
    double *scores=NULL;
    char *result=NULL;

    if(!utf8_text||!*utf8_text)return str_dup_len("",0);
    if(percent<0.1||percent>100.0)percent=10.0;
    text_len=strlen(utf8_text);
    budget=(size_t)((double)text_len*percent/100.0);
    if(budget<1)budget=1;
    if(percent>=100.0||budget>=text_len)return str_dup_len(utf8_text,text_len);

    sentence_array_init(&sentences);
    candidate_array_init(&candidates);
    if(!candidate_hash_init(&candidates,16384))goto cleanup;

    while(p<text_len){
        size_t used;unsigned int cp=utf8_decode(utf8_text+p,text_len-p,&used);
        if(!used)break;
        if(cp=='\n'){
            size_t len=p-start;
            while(len&&((unsigned char)utf8_text[start+len-1]=='\r'||utf8_text[start+len-1]==' '))len--;
            if(len>5&&!sentence_array_push(&sentences,utf8_text+start,len,line))goto cleanup;
            line++;start=p+used;
        }else if(cp==0x3002||cp==0xFF01||cp==0xFF1F||cp=='!'||cp=='?'||cp==0x2026){
            size_t end=p+used;
            while(end<text_len){
                size_t u;unsigned int x=utf8_decode(utf8_text+end,text_len-end,&u);
                if(!u||!is_space_cp(x))break;
                end+=u;
            }
            if(end-start>5&&!sentence_array_push(&sentences,utf8_text+start,end-start,line))goto cleanup;
            start=end;p=end;continue;
        }
        p+=used;
    }
    if(start<text_len){
        size_t len=text_len-start;
        while(len&&((unsigned char)utf8_text[start+len-1]=='\r'||utf8_text[start+len-1]==' '))len--;
        if(len>5&&!sentence_array_push(&sentences,utf8_text+start,len,line))goto cleanup;
    }
    if(!sentences.count)goto cleanup;

    for(i=0;i<sentences.count;i++)
        if(!process_sentence(&sentences.data[i],i,&candidates,&sentences))goto cleanup;

    scores=(double*)calloc(sentences.count,sizeof(double));
    if(!scores)goto cleanup;

    for(i=0;i<candidates.count;i++){
        Candidate *c=&candidates.data[i];
        size_t j,f=c->sentence_count;
        double spread=(double)f/(double)sentences.count;
        double penalty=1.0;
        if(c->weight>(double)sentences.count*.2)penalty=.35;
        else if(c->weight>(double)sentences.count*.1)penalty=.55;
        else if(c->weight>(double)sentences.count*.05)penalty=.8;
        double length_score=fmin(4.0,1.0+cp_count(c->text,c->len)/5.0);
        unsigned int mask=c->type_mask;
        int types=0;
        while(mask){types+=mask&1;mask>>=1;}
        double type_bonus=fmin(4.0,1.0+types*.8);
        double frequency_score=fmin(5.0,1.0+log2(c->weight+1.0));
        double score=length_score*type_bonus*frequency_score*(1.0+spread*3.0)*penalty;
        for(j=0;j<f;j++)scores[c->sentences[j]]+=score;
    }

    for(i=0;i<sentences.count;i++){
        const char *s=sentences.data[i].text;size_t len=sentences.data[i].len,q=0;
        int kanji=0,katakana=0,numbers=0,upper=0,mixed=0,last=0;
        while(q<len){
            size_t u;unsigned int cp=utf8_decode(s+q,len-q,&u);
            if(!u)break;
            if(is_kanji(cp)){kanji++;if(last==2)mixed=1;last=1;}
            else if(is_katakana(cp)){katakana++;if(last==1)mixed=1;last=2;}
            else if(cp<128&&isdigit((unsigned char)cp)){numbers++;last=0;}
            else if(cp<128&&is_ascii_upper(cp)){upper=1;last=0;}
            else last=0;
            q+=u;
        }
        scores[i]+=fmin(6.0,kanji*.25);
        scores[i]+=fmin(6.0,katakana*.35);
        scores[i]+=fmin(3.0,numbers*.8);
        if(upper)scores[i]+=3.0;
        if(mixed)scores[i]+=4.0;
        scores[i]+=fmin(2.0,(double)len/300.0);
        sentences.data[i].score=scores[i];
    }

    ranked=(Sentence**)malloc(sentences.count*sizeof(Sentence*));
    if(!ranked)goto cleanup;
    for(i=0;i<sentences.count;i++)ranked[i]=&sentences.data[i];
    qsort(ranked,sentences.count,sizeof(Sentence*),rank_compare);

    selected_flags=(unsigned char*)calloc(sentences.count,1);
    used_candidate=(unsigned char*)calloc(candidates.count,1);
    selected=(size_t*)malloc(sentences.count*sizeof(size_t));
    if(!selected_flags||!used_candidate||!selected)goto cleanup;

    {
        size_t current=0;
        while(current<budget){
            size_t best=SIZE_MAX,k;
            double best_score=-1.0;
            size_t limit=sentences.count<2001?sentences.count:2001;

            for(k=0;k<limit;k++){
                Sentence *s=ranked[k];
                size_t idx=(size_t)(s-sentences.data),j,newc=0;
                double score;
                int nearby=0;
                if(selected_flags[idx]||current+s->len>budget)continue;
                for(j=0;j<s->candidate_count;j++)
                    if(!used_candidate[s->candidates[j]])newc++;
                score=s->score+newc*2.5;
                for(j=0;j<selected_count;j++){
                    size_t x=selected[j];
                    size_t a=s->line>sentences.data[x].line?s->line:sentences.data[x].line;
                    size_t b=s->line<sentences.data[x].line?s->line:sentences.data[x].line;
                    if(a-b<=2){nearby=1;break;}
                }
                if(nearby)score*=.65;
                if(score>best_score){best_score=score;best=idx;}
            }
            if(best==SIZE_MAX)break;
            selected_flags[best]=1;
            selected[selected_count++]=best;
            current+=sentences.data[best].len;
            for(k=0;k<sentences.data[best].candidate_count;k++)
                used_candidate[sentences.data[best].candidates[k]]=1;
        }
    }

    qsort(selected,selected_count,sizeof(size_t),index_compare);
    result=build_result(&sentences,selected,selected_count,budget);

cleanup:
    free(scores);free(selected_flags);free(used_candidate);free(ranked);free(selected);
    sentence_array_free(&sentences);
    candidate_array_free(&candidates);
    if(!result)result=str_dup_len("",0);
    return result;
}

GLOSSARY_API void glossary_free(char *ptr){free(ptr);}