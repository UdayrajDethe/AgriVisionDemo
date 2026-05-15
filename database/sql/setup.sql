BEGIN
  EXECUTE IMMEDIATE '
    CREATE TABLE CROP_ANALYSES (
      ID NUMBER PRIMARY KEY,
      CROP_NAME VARCHAR2(100) NOT NULL,
      STATUS VARCHAR2(20) NOT NULL,
      CREATED_AT DATE DEFAULT SYSDATE NOT NULL,
      HEALTH_SCORE NUMBER(3)
    )';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'CREATE SEQUENCE CROP_ANALYSES_SEQ START WITH 1 INCREMENT BY 1';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF;
END;
/

CREATE OR REPLACE TRIGGER CROP_ANALYSES_BI
BEFORE INSERT ON CROP_ANALYSES
FOR EACH ROW
BEGIN
  IF :NEW.ID IS NULL THEN
    SELECT CROP_ANALYSES_SEQ.NEXTVAL INTO :NEW.ID FROM DUAL;
  END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE '
    CREATE TABLE AGRIVISION_USERS (
      ID NUMBER PRIMARY KEY,
      USER_ID VARCHAR2(40) NOT NULL,
      NAME VARCHAR2(100) NOT NULL,
      EMAIL VARCHAR2(150) NOT NULL,
      PHONE VARCHAR2(20),
      PASSWORD_HASH VARCHAR2(200) NOT NULL,
      LOCATION VARCHAR2(150),
      CREATED_AT DATE DEFAULT SYSDATE NOT NULL,
      CONSTRAINT AGRIVISION_USERS_EMAIL_UQ UNIQUE (EMAIL)
    )';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'CREATE SEQUENCE AGRIVISION_USERS_SEQ START WITH 1 INCREMENT BY 1';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF;
END;
/

CREATE OR REPLACE TRIGGER AGRIVISION_USERS_BI
BEFORE INSERT ON AGRIVISION_USERS
FOR EACH ROW
BEGIN
  IF :NEW.ID IS NULL THEN
    SELECT AGRIVISION_USERS_SEQ.NEXTVAL INTO :NEW.ID FROM DUAL;
  END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE '
    CREATE TABLE AGRIVISION_DISEASES (
      ID NUMBER PRIMARY KEY,
      DISEASE_ID VARCHAR2(40) NOT NULL,
      NAME VARCHAR2(120) NOT NULL,
      CROP_NAME VARCHAR2(100),
      IS_HEALTHY CHAR(1) DEFAULT ''N'' NOT NULL,
      SYMPTOMS CLOB,
      TREATMENT CLOB,
      PREVENTION CLOB,
      DESCRIPTION CLOB,
      CREATED_AT DATE DEFAULT SYSDATE NOT NULL,
      CONSTRAINT AGRIVISION_DISEASES_NAME_UQ UNIQUE (NAME)
    )';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'ALTER TABLE AGRIVISION_DISEASES ADD IS_HEALTHY CHAR(1) DEFAULT ''N'' NOT NULL';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -1430 THEN RAISE; END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'CREATE SEQUENCE AGRIVISION_DISEASES_SEQ START WITH 1 INCREMENT BY 1';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF;
END;
/

CREATE OR REPLACE TRIGGER AGRIVISION_DISEASES_BI
BEFORE INSERT ON AGRIVISION_DISEASES
FOR EACH ROW
BEGIN
  IF :NEW.ID IS NULL THEN
    SELECT AGRIVISION_DISEASES_SEQ.NEXTVAL INTO :NEW.ID FROM DUAL;
  END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE '
    CREATE TABLE AGRIVISION_ANALYSES (
      ID NUMBER PRIMARY KEY,
      ANALYSIS_ID VARCHAR2(40) NOT NULL,
      USER_ID VARCHAR2(40),
      DISEASE_ID VARCHAR2(40),
      IMAGE_NAME VARCHAR2(255),
      PREDICTED_LABEL VARCHAR2(150),
      CONFIDENCE NUMBER(8, 4),
      ROBOFLOW_RESPONSE CLOB,
      CREATED_AT DATE DEFAULT SYSDATE NOT NULL
    )';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'CREATE SEQUENCE AGRIVISION_ANALYSES_SEQ START WITH 1 INCREMENT BY 1';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -955 THEN RAISE; END IF;
END;
/

CREATE OR REPLACE TRIGGER AGRIVISION_ANALYSES_BI
BEFORE INSERT ON AGRIVISION_ANALYSES
FOR EACH ROW
BEGIN
  IF :NEW.ID IS NULL THEN
    SELECT AGRIVISION_ANALYSES_SEQ.NEXTVAL INTO :NEW.ID FROM DUAL;
  END IF;
END;
/

MERGE INTO AGRIVISION_DISEASES target
USING (
  SELECT 'POTATO_LATE_BLIGHT' DISEASE_ID, 'Potato Late Blight' NAME, 'Potato' CROP_NAME, 'N' IS_HEALTHY,
         'Water-soaked leaf spots that turn brown or black, white fungal growth in humid weather, and fast leaf collapse.' SYMPTOMS,
         'Remove infected leaves, avoid overhead watering, improve airflow, and apply a recommended fungicide for late blight.' TREATMENT,
         'Use certified seed potatoes, rotate crops, keep foliage dry, and monitor fields closely during cool wet weather.' PREVENTION,
         'A destructive potato disease commonly caused by Phytophthora infestans.' DESCRIPTION FROM DUAL
  UNION ALL SELECT 'POTATO_HEALTHY', 'Potato healthy', 'Potato', 'Y',
         'No visible disease symptoms; leaves appear green and evenly developed.',
         'No treatment needed. Continue regular monitoring and balanced irrigation.',
         'Maintain good field sanitation, crop rotation, and regular scouting.',
         'Healthy potato leaf class from the trained model.' FROM DUAL
  UNION ALL SELECT 'POTATO_EARLY_BLIGHT', 'Potato_Early_blight', 'Potato', 'N',
         'Dark brown leaf spots with concentric rings, usually starting on older lower leaves.',
         'Remove infected foliage where practical and use an appropriate fungicide if disease pressure is high.',
         'Rotate crops, avoid plant stress, mulch to reduce soil splash, and remove plant debris after harvest.',
         'A fungal potato leaf disease often associated with Alternaria species.' FROM DUAL
  UNION ALL SELECT 'TOMATO_BACTERIAL_SPOT', 'Tomato Bacterial spot', 'Tomato', 'N',
         'Small dark water-soaked leaf spots, yellow halos, and rough scabby spots on fruit.',
         'Remove badly affected leaves and use copper-based bactericides where locally recommended.',
         'Use disease-free seed, avoid overhead watering, disinfect tools, and rotate away from tomato and pepper.',
         'A bacterial disease that spreads quickly in warm wet conditions.' FROM DUAL
  UNION ALL SELECT 'TOMATO_EARLY_BLIGHT', 'Tomato Early Blight', 'Tomato', 'N',
         'Brown target-like rings on older leaves, yellowing around lesions, and lower leaf drop.',
         'Prune infected lower leaves, improve airflow, and apply a suitable fungicide when needed.',
         'Stake plants, mulch soil, rotate crops, and remove infected debris.',
         'A common tomato fungal disease caused mainly by Alternaria solani.' FROM DUAL
  UNION ALL SELECT 'TOMATO_HEALTHY', 'Tomato Healthy', 'Tomato', 'Y',
         'No visible disease symptoms; leaves are green, firm, and normally shaped.',
         'No treatment needed. Keep monitoring plant health.',
         'Use balanced watering, clean tools, good spacing, and regular scouting.',
         'Healthy tomato leaf class from the trained model.' FROM DUAL
  UNION ALL SELECT 'TOMATO_LATE_BLIGHT', 'Tomato Late Blight', 'Tomato', 'N',
         'Large irregular dark lesions, pale green water-soaked areas, and rapid leaf or stem collapse.',
         'Remove infected material, avoid wet foliage, and apply a late-blight fungicide as advised locally.',
         'Use resistant varieties where possible, increase plant spacing, and avoid overhead irrigation.',
         'A serious tomato disease commonly caused by Phytophthora infestans.' FROM DUAL
  UNION ALL SELECT 'TOMATO_LEAF_MOLD', 'Tomato Leaf Mold', 'Tomato', 'N',
         'Yellow patches on upper leaf surfaces with olive-gray mold growth underneath.',
         'Improve ventilation, remove infected leaves, and use a labeled fungicide if necessary.',
         'Reduce humidity, space plants well, and avoid prolonged leaf wetness.',
         'A tomato leaf disease favored by high humidity and poor airflow.' FROM DUAL
  UNION ALL SELECT 'TOMATO_MOSAIC_VIRUS', 'Tomato mosaic virus', 'Tomato', 'N',
         'Mottled light and dark green leaf pattern, distorted leaves, and reduced plant growth.',
         'No cure for infected plants. Remove infected plants and control spread through sanitation.',
         'Use resistant varieties, wash hands and tools, and avoid handling plants when wet.',
         'A viral tomato disease that spreads through contact and contaminated tools.' FROM DUAL
  UNION ALL SELECT 'TOMATO_TARGET_SPOT', 'Tomato_Target_Spot', 'Tomato', 'N',
         'Small brown lesions that enlarge into target-like spots, often with yellowing tissue around them.',
         'Remove infected leaves, increase airflow, and use appropriate fungicides when disease is spreading.',
         'Avoid overhead watering, rotate crops, and remove crop residue.',
         'A fungal tomato disease that can reduce foliage and fruit quality.' FROM DUAL
  UNION ALL SELECT 'TOMATO_YELLOW_LEAF_CURL_VIRUS', 'Tomato_YellowLeaf__Curl_Viru', 'Tomato', 'N',
         'Yellowing, upward leaf curling, stunted growth, and poor fruit set.',
         'There is no cure. Remove infected plants and manage whitefly populations.',
         'Use resistant varieties, control whiteflies, remove weeds, and protect seedlings with netting.',
         'A viral tomato disease commonly spread by whiteflies.' FROM DUAL
) source
ON (target.DISEASE_ID = source.DISEASE_ID)
WHEN MATCHED THEN UPDATE SET
  target.NAME = source.NAME,
  target.CROP_NAME = source.CROP_NAME,
  target.IS_HEALTHY = source.IS_HEALTHY,
  target.SYMPTOMS = source.SYMPTOMS,
  target.TREATMENT = source.TREATMENT,
  target.PREVENTION = source.PREVENTION,
  target.DESCRIPTION = source.DESCRIPTION
WHEN NOT MATCHED THEN INSERT
  (DISEASE_ID, NAME, CROP_NAME, IS_HEALTHY, SYMPTOMS, TREATMENT, PREVENTION, DESCRIPTION)
VALUES
  (source.DISEASE_ID, source.NAME, source.CROP_NAME, source.IS_HEALTHY, source.SYMPTOMS,
   source.TREATMENT, source.PREVENTION, source.DESCRIPTION);

COMMIT;
