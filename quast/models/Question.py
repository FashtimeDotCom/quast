import logging
from typing import List

from psycopg2.pool import ThreadedConnectionPool

from quast.models.Answer import Answer


logger = logging.getLogger(__name__)


class Question:
    """
    Class representing a Question.
    """

    def __init__(self,
                 author: str = None,
                 title: str = None,
                 body: str = None,
                 upvotes: int = 0,
                 downvotes: int = 0,
                 qid: int = None,
                 tags: List[str] = None,
                 pool: ThreadedConnectionPool = None) -> (None):
        self._author = author
        self._title = title
        self._body = body
        self._upvotes = int(upvotes) if upvotes else 0
        self._downvotes = int(downvotes) if downvotes else 0
        self._pool = pool
        self._qid = qid
        self._tags = tags

    @staticmethod
    def from_qid(qid: int,
                 pool: ThreadedConnectionPool):
        """
        Construct ``Question`` from ``qid``.
        """
        conn = pool.getconn()
        with conn.cursor() as curs:
            curs.execute("SELECT author, title, description, upvotes, downvotes "
                         "FROM questions "
                         "WHERE qid=%s", (qid, ))
            author, title, body, upvotes, downvotes = curs.fetchone()
            curs.execute("SELECT tag FROM question_tags WHERE qid=%s", (qid, ))
            tags = [res[0] for res in curs]
        pool.putconn(conn)
        return Question(author=author, title=title, body=body, upvotes=upvotes,
                        downvotes=downvotes, qid=qid, pool=pool, tags=tags)

    @staticmethod
    def create(author, title, body, tags, pool):
        """
        Create a new question, store it in DB.
        """
        conn = pool.getconn()
        with conn.cursor() as curs:
            curs.execute("INSERT INTO questions(author, title, description) "
                         "VALUES(%(author)s, %(title)s, %(body)s)",
                         {'author': author, 'title': title, 'body': body})
            conn.commit()
            curs.execute("SELECT qid FROM questions WHERE author=%s AND title=%s ",
                         (author, title))
            (qid, ) = curs.fetchone()
            for tag in tags:
                curs.execute("INSERT INTO question_tags(tag, qid) VALUES(%s, %s) ",
                             (tag, qid))
            conn.commit()
        pool.putconn(conn)
        return Question(author=author, title=title, body=body, tags=tags,
                        pool=pool, qid=qid)

    def answers(self):
        """
        Return a list of ``quast.models.Answer`` object.
        """
        conn = self._pool.getconn()
        answers = []
        with conn.cursor() as curs:
            curs.execute("SELECT author, body, upvotes, downvotes FROM answers "
                         "WHERE qid=%s", (self._qid, ))
            for author, body, upvotes, downvotes in curs:
                answers.append(Answer(author=author, body=body, upvotes=upvotes,
                                      downvotes=downvotes, qid=self._qid,
                                      pool=self._pool))
        self._pool.putconn(conn)
        return answers

    def as_dict(self):
        """
        Return relevant information of ``Question`` in form of dict.
        """
        return {
            'author': self._author,
            'title': self._title,
            'description': self._body,
            'upvotes': self._upvotes,
            'downvotes': self._downvotes,
            'qid': self._qid,
            'tags': self._tags
        }

    def __eq__(self, other):
        return (
            self._author == other._author and
            self._title == other._title and
            self._body == other._body and
            self._upvotes == other._upvotes and
            self._downvotes == other._downvotes and
            self._qid == other._qid and
            self._tags == other._tags
        )

    def __repr__(self):
        return "<Question: (qid={})>".format(self._qid)

    def delete(self):
        """
        Delete question using qid.
        :returns: ``True`` if successful else ``False``.
        """
        conn = self._pool.getconn()
        try:
            with conn.cursor() as curs:
                curs.execute("DELETE FROM questions WHERE qid=%s",
                             (self._qid, ))
            conn.commit()
            return True
        except:  # pragma: no cover, # for logging
            logger.exception("An exception occured while deleting question"
                             " {}".format(self))
            return False
        finally:
            self._pool.putconn(conn)
