#ifndef GLOSSARY_FAST_H
#define GLOSSARY_FAST_H

#ifdef _WIN32
#define GLOSSARY_API __declspec(dllexport)
#else
#define GLOSSARY_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

GLOSSARY_API char* glossary_extract_sample(
    const char* utf8_text,
    double percent
);

GLOSSARY_API void glossary_free(char* ptr);

#ifdef __cplusplus
}
#endif

#endif