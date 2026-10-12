-- Allergen synonym seed: EU Reg. 1169/2011 Annex II (14) + FDA Top 9.
-- canonical = the allergen the user declares; synonym = what may appear on a label.
-- match_type 'contains' = substring match; 'exact' = whole-token match (avoids false hits).
-- This is a STARTER set (~120 rows). Expand from FARE / Anaphylaxis UK derivative lists.

-- ===== MILK =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('milk','milk','contains'),('milk','dairy','contains'),('milk','butter','contains'),
('milk','casein','contains'),('milk','caseinate','contains'),('milk','whey','contains'),
('milk','lactose','contains'),('milk','lactalbumin','contains'),('milk','lactoglobulin','contains'),
('milk','cream','contains'),('milk','cheese','contains'),('milk','yogurt','contains'),
('milk','yoghurt','contains'),('milk','ghee','contains'),('milk','curd','contains'),
('milk','custard','contains'),('milk','paneer','contains'),('milk','e966','exact'),
('milk','lactitol','contains'),('milk','milk solids','contains'),('milk','skimmed milk powder','contains');

-- ===== EGG =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('egg','egg','contains'),('egg','albumin','contains'),('egg','albumen','contains'),
('egg','ovalbumin','contains'),('egg','globulin','contains'),('egg','livetin','contains'),
('egg','lysozyme','contains'),('egg','e1105','exact'),('egg','mayonnaise','contains'),
('egg','meringue','contains'),('egg','ovomucoid','contains'),('egg','vitellin','contains');

-- ===== PEANUT =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('peanut','peanut','contains'),('peanut','groundnut','contains'),('peanut','arachis','contains'),
('peanut','goober','contains'),('peanut','monkey nut','contains'),('peanut','beer nut','contains'),
('peanut','mandelona','contains'),('peanut','arachis oil','contains');

-- ===== TREE NUTS =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('tree nut','almond','contains'),('tree nut','hazelnut','contains'),('tree nut','walnut','contains'),
('tree nut','cashew','contains'),('tree nut','pecan','contains'),('tree nut','pistachio','contains'),
('tree nut','brazil nut','contains'),('tree nut','macadamia','contains'),('tree nut','pine nut','contains'),
('tree nut','praline','contains'),('tree nut','marzipan','contains'),('tree nut','nougat','contains'),
('tree nut','frangipane','contains'),('tree nut','gianduja','contains'),('tree nut','nut','exact');

-- ===== SOY =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('soy','soy','contains'),('soy','soya','contains'),('soy','soybean','contains'),
('soy','edamame','contains'),('soy','tofu','contains'),('soy','tempeh','contains'),
('soy','miso','contains'),('soy','tamari','contains'),('soy','tvp','exact'),
('soy','lecithin','contains'),('soy','e322','exact'),('soy','natto','contains');

-- ===== WHEAT / GLUTEN =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('wheat','wheat','contains'),('wheat','gluten','contains'),('wheat','flour','contains'),
('wheat','barley','contains'),('wheat','rye','contains'),('wheat','malt','contains'),
('wheat','semolina','contains'),('wheat','spelt','contains'),('wheat','durum','contains'),
('wheat','farro','contains'),('wheat','couscous','contains'),('wheat','bulgur','contains'),
('wheat','seitan','contains'),('wheat','bran','contains'),('wheat','triticale','contains'),
('wheat','kamut','contains');

-- ===== FISH =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('fish','fish','contains'),('fish','salmon','contains'),('fish','tuna','contains'),
('fish','cod','contains'),('fish','anchovy','contains'),('fish','anchovies','contains'),
('fish','sardine','contains'),('fish','mackerel','contains'),('fish','haddock','contains'),
('fish','worcestershire','contains'),('fish','fish sauce','contains'),('fish','surimi','contains'),
('fish','caviar','contains'),('fish','roe','contains');

-- ===== CRUSTACEAN SHELLFISH =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('shellfish','shrimp','contains'),('shellfish','prawn','contains'),('shellfish','crab','contains'),
('shellfish','lobster','contains'),('shellfish','crayfish','contains'),('shellfish','langoustine','contains'),
('shellfish','krill','contains'),('shellfish','scampi','contains'),('shellfish','crustacean','contains');

-- ===== MOLLUSCS =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('mollusc','mussel','contains'),('mollusc','clam','contains'),('mollusc','oyster','contains'),
('mollusc','squid','contains'),('mollusc','calamari','contains'),('mollusc','octopus','contains'),
('mollusc','scallop','contains'),('mollusc','snail','contains'),('mollusc','escargot','contains'),
('mollusc','cuttlefish','contains'),('mollusc','abalone','contains');

-- ===== SESAME =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('sesame','sesame','contains'),('sesame','tahini','contains'),('sesame','benne','contains'),
('sesame','gingelly','contains'),('sesame','til','exact'),('sesame','halvah','contains');

-- ===== MUSTARD =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('mustard','mustard','contains'),('mustard','dijon','contains'),('mustard','wholegrain mustard','contains');

-- ===== CELERY =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('celery','celery','contains'),('celery','celeriac','contains'),('celery','celery salt','contains');

-- ===== LUPIN =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('lupin','lupin','contains'),('lupin','lupine','contains'),('lupin','lupin flour','contains');

-- ===== SULPHITES =====
INSERT INTO allergen_synonyms (canonical, synonym, match_type) VALUES
('sulphite','sulphite','contains'),('sulphite','sulfite','contains'),('sulphite','sulphur dioxide','contains'),
('sulphite','e220','exact'),('sulphite','e221','exact'),('sulphite','e222','exact'),
('sulphite','e223','exact'),('sulphite','e224','exact'),('sulphite','e226','exact'),
('sulphite','e227','exact'),('sulphite','e228','exact'),('sulphite','metabisulphite','contains');

-- ===== FALSE-POSITIVE GUARDS =====
-- Substring matching would wrongly flag these; the gate skips a hit if the
-- ingredient matches one of these patterns for that canonical allergen.
INSERT INTO synonym_exceptions (canonical, pattern) VALUES
('milk','coconut milk'),('milk','coconut cream'),('milk','almond milk'),('milk','soy milk'),
('milk','oat milk'),('milk','rice milk'),('milk','cocoa butter'),('milk','shea butter'),
('milk','peanut butter'),('milk','milk thistle'),('milk','butternut'),('milk','buttermilk substitute'),
('tree nut','nutmeg'),('tree nut','water chestnut'),('tree nut','butternut'),('tree nut','nut-free'),
('tree nut','coconut'),('peanut','peanut-free'),('soy','soy-free'),('wheat','buckwheat'),
('wheat','wheatgrass'),('wheat','flourish');
