CREATE TABLE articles_source (
    id bigint NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,
    url VARCHAR(500) NOT NULL,
    active boolean NOT NULL,
    CONSTRAINT articles_source_pkey PRIMARY KEY (id)
);

CREATE TABLE articles_tag (
    id bigint NOT NULL,
    label VARCHAR(100) NOT NULL,
    CONSTRAINT articles_tag_label_key UNIQUE (label),
    CONSTRAINT articles_tag_pkey PRIMARY KEY (id)
);

CREATE TABLE auth_user (
    id integer NOT NULL,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMPTZ,
    is_superuser boolean NOT NULL,
    username VARCHAR(150) NOT NULL,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined TIMESTAMPTZ NOT NULL,
    CONSTRAINT auth_user_pkey PRIMARY KEY (id),
    CONSTRAINT auth_user_username_key UNIQUE (username)
);

CREATE TABLE digests_digest (
    id bigint NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    article_count integer NOT NULL,
    CONSTRAINT digests_digest_pkey PRIMARY KEY (id)
);

CREATE TABLE articles_article (
    id bigint NOT NULL,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(500) NOT NULL,
    published_at TIMESTAMPTZ,
    raw_score integer NOT NULL,
    is_read boolean NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    source_id bigint NOT NULL,
    CONSTRAINT articles_article_pkey PRIMARY KEY (id),
    CONSTRAINT articles_article_url_ab2a9363_uniq UNIQUE (url),
    CONSTRAINT articles_article_source_id_9a8869ea_fk_articles_source_id FOREIGN KEY (source_id) REFERENCES articles_source(id)
);

CREATE TABLE user_profiles_userkeyword (
    id bigint NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    weight integer NOT NULL,
    user_id integer NOT NULL,
    CONSTRAINT unique_user_keyword UNIQUE (user_id, keyword),
    CONSTRAINT user_profiles_userkeyword_pkey PRIMARY KEY (id),
    CONSTRAINT user_profiles_userkeyword_user_id_b3060d40_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user(id)
);

CREATE TABLE articles_article_tags (
    id bigint NOT NULL,
    article_id bigint NOT NULL,
    tag_id bigint NOT NULL,
    CONSTRAINT articles_article_tags_article_id_tag_id_1988a91e_uniq UNIQUE (article_id, tag_id),
    CONSTRAINT articles_article_tags_pkey PRIMARY KEY (id),
    CONSTRAINT articles_article_tag_article_id_524565b8_fk_articles_ FOREIGN KEY (article_id) REFERENCES articles_article(id),
    CONSTRAINT articles_article_tags_tag_id_56ec02c6_fk_articles_tag_id FOREIGN KEY (tag_id) REFERENCES articles_tag(id)
);

CREATE TABLE articles_vote (
    id bigint NOT NULL,
    direction VARCHAR(10),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    article_id bigint NOT NULL,
    user_id integer NOT NULL,
    CONSTRAINT articles_vote_pkey PRIMARY KEY (id),
    CONSTRAINT unique_user_article_vote UNIQUE (user_id, article_id),
    CONSTRAINT articles_vote_article_id_cf80085a_fk_articles_article_id FOREIGN KEY (article_id) REFERENCES articles_article(id),
    CONSTRAINT articles_vote_user_id_10272b31_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user(id)
);

CREATE TABLE digests_digestitem (
    id bigint NOT NULL,
    rank integer NOT NULL,
    article_id bigint NOT NULL,
    digest_id bigint NOT NULL,
    CONSTRAINT digests_digestitem_pkey PRIMARY KEY (id),
    CONSTRAINT unique_digest_article UNIQUE (digest_id, article_id),
    CONSTRAINT digests_digestitem_article_id_88472ac0_fk_articles_article_id FOREIGN KEY (article_id) REFERENCES articles_article(id),
    CONSTRAINT digests_digestitem_digest_id_2f190435_fk_digests_digest_id FOREIGN KEY (digest_id) REFERENCES digests_digest(id)
);
