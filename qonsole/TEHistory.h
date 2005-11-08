/* -------------------------------------------------------------------------- */
/*                                                                            */
/* [TEHistory.H]                   History Buffer                             */
/*                                                                            */
/* -------------------------------------------------------------------------- */
/*                                                                            */
/* Copyright (c) 1997,1998 by Lars Doelle <lars.doelle@on-line.de>            */
/*                                                                            */
/* This file is part of Konsole - an X terminal for KDE                       */
/*                                                                            */
/* -------------------------------------------------------------------------- */

#ifndef TEHISTORY_H
#define TEHISTORY_H

#include <qcstring.h>
#include <qptrvector.h>
#include <qbitarray.h>
#include <qintdict.h>

#include "TECommon.h"
#include "BlockArray.h"


//////////////////////////////////////////////////////////////////////

//////////////////////////////////////////////////////////////////////
// Abstract base class for file and buffer versions
//////////////////////////////////////////////////////////////////////
class HistoryType;

class HistoryScroll
{
public:
  HistoryScroll(HistoryType*);
 virtual ~HistoryScroll();

  virtual bool hasScroll();

  // access to history
  virtual int  getLines() = 0;
  virtual int  getLineLen(int lineno) = 0;
  virtual void getCells(int lineno, int colno, int count, ca res[]) = 0;
  virtual bool isWrappedLine(int lineno) = 0;

  // backward compatibility (obsolete)
  ca   getCell(int lineno, int colno) { ca res; getCells(lineno,colno,1,&res); return res; }

  // adding lines.
  virtual void addCells(ca a[], int count) = 0;
  virtual void addLine(bool previousWrapped=false) = 0;

  const HistoryType& getType() { return *m_histType; }

protected:
  HistoryType* m_histType;
};


//////////////////////////////////////////////////////////////////////
// Buffer-based history (limited to a fixed nb of lines)
//////////////////////////////////////////////////////////////////////
class HistoryScrollBuffer : public HistoryScroll
{
public:
  typedef QMemArray<ca> histline;

  HistoryScrollBuffer(unsigned int maxNbLines = 1000);
  virtual ~HistoryScrollBuffer();

  virtual int  getLines();
  virtual int  getLineLen(int lineno);
  virtual void getCells(int lineno, int colno, int count, ca res[]);
  virtual bool isWrappedLine(int lineno);

  virtual void addCells(ca a[], int count);
  virtual void addLine(bool previousWrapped=false);

  void setMaxNbLines(unsigned int nbLines);
  unsigned int maxNbLines() { return m_maxNbLines; }
  

private:
  int adjustLineNb(int lineno);

  // Normalize buffer so that the size can be changed.
  void normalize();

  bool m_hasScroll;
  QPtrVector<histline> m_histBuffer;
  QBitArray m_wrappedLine;
  unsigned int m_maxNbLines;
  unsigned int m_nbLines;
  unsigned int m_arrayIndex;
  bool         m_buffFilled;

};


//////////////////////////////////////////////////////////////////////
// Nothing-based history (no history :-)
//////////////////////////////////////////////////////////////////////
class HistoryScrollNone : public HistoryScroll
{
public:
  HistoryScrollNone();
  virtual ~HistoryScrollNone();

  virtual bool hasScroll();

  virtual int  getLines();
  virtual int  getLineLen(int lineno);
  virtual void getCells(int lineno, int colno, int count, ca res[]);
  virtual bool isWrappedLine(int lineno);

  virtual void addCells(ca a[], int count);
  virtual void addLine(bool previousWrapped=false);
};


//////////////////////////////////////////////////////////////////////
// BlockArray-based history
//////////////////////////////////////////////////////////////////////
class HistoryScrollBlockArray : public HistoryScroll
{
public:
  HistoryScrollBlockArray(size_t size);
  virtual ~HistoryScrollBlockArray();

  virtual int  getLines();
  virtual int  getLineLen(int lineno);
  virtual void getCells(int lineno, int colno, int count, ca res[]);
  virtual bool isWrappedLine(int lineno);

  virtual void addCells(ca a[], int count);
  virtual void addLine(bool previousWrapped=false);

protected:
  BlockArray m_blockArray;
  QIntDict<size_t> m_lineLengths;
};


//////////////////////////////////////////////////////////////////////
// History type
//////////////////////////////////////////////////////////////////////
class HistoryType
{
public:
  HistoryType();
  virtual ~HistoryType();

  virtual bool isOn()                const = 0;
  virtual unsigned int getSize()     const = 0;

  virtual HistoryScroll* getScroll(HistoryScroll *) const = 0;
};

class HistoryTypeNone : public HistoryType
{
public:
  HistoryTypeNone();

  virtual bool isOn() const;
  virtual unsigned int getSize() const;

  virtual HistoryScroll* getScroll(HistoryScroll *) const;
};

class HistoryTypeBlockArray : public HistoryType
{
public:
  HistoryTypeBlockArray(size_t size);
  
  virtual bool isOn() const;
  virtual unsigned int getSize() const;

  virtual HistoryScroll* getScroll(HistoryScroll *) const;

protected:
  size_t m_size;
};


class HistoryTypeBuffer : public HistoryType
{
public:
  HistoryTypeBuffer(unsigned int nbLines);
  
  virtual bool isOn() const;
  virtual unsigned int getNbLines() const;
  virtual unsigned int getSize() const;

  virtual HistoryScroll* getScroll(HistoryScroll *) const;

protected:
  unsigned int m_nbLines;
};

#endif // TEHISTORY_H
