CREATE TABLE task (
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  title STRING(255) NOT NULL,
  description TEXT,
  done INTEGER NOT NULL DEFAULT 0
);

INSERT INTO task VALUES (
  1,'Buy groceries','Milk, Cheese, Pizza, Fruit, Tylenol',0
), (
  2,'Learn Python','Neet to find a good Python tutorial on the web',0
);
