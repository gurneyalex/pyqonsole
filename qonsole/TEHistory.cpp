/* -------------------------------------------------------------------------- */
/*                                                                            */
/* [TEHistory.C]                   History Buffer                             */
/*                                                                            */
/* -------------------------------------------------------------------------- */
/*                                                                            */
/* Copyright (c) 1997,1998 by Lars Doelle <lars.doelle@on-line.de>            */
/*                                                                            */
/* This file is part of Konsole - an X terminal for KDE                       */
/*                                                                            */
/* -------------------------------------------------------------------------- */

#include "TEHistory.h"

#include <iostream>
#include <stdlib.h>
#include <assert.h>
#include <stdio.h>
#include <sys/types.h>
#include <unistd.h>
#include <errno.h>

// Reasonable line size
#define LINE_SIZE	1024

/*
   An arbitrary long scroll.

   One can modify the scroll only by adding either cells
   or newlines, but access it randomly.

   The model is that of an arbitrary wide typewriter scroll
   in that the scroll is a serie of lines and each line is
   a serie of cells with no overwriting permitted.

   The implementation provides arbitrary length and numbers
   of cells and line/column indexed read access to the scroll
   at constant costs.

FIXME: some complain about the history buffer comsuming the
       memory of their machines. This problem is critical
       since the history does not behave gracefully in cases
       where the memory is used up completely.

       I put in a workaround that should handle it problem
       now gracefully. I'm not satisfied with the solution.

FIXME: Terminating the history is not properly indicated
       in the menu. We should throw a signal.

FIXME: There is noticable decrease in speed, also. Perhaps,
       there whole feature needs to be revisited therefore.
       Disadvantage of a more elaborated, say block-oriented
       scheme with wrap around would be it's complexity.
*/

//FIXME: tempory replacement for tmpfile
//       this is here one for debugging purpose.

//#define tmpfile xTmpFile

// History File ///////////////////////////////////////////

/*
  A Row(X) data type which allows adding elements to the end.
*/


// History Scroll abstract base class //////////////////////////////////////
HistoryScroll::HistoryScroll(HistoryType* t)
  : m_histType(t)
{
}

HistoryScroll::~HistoryScroll()
{
  delete m_histType;
}

bool HistoryScroll::hasScroll()
{
  return true;
}


// History Scroll Buffer //////////////////////////////////////
HistoryScrollBuffer::HistoryScrollBuffer(unsigned int maxNbLines)
  : HistoryScroll(new HistoryTypeBuffer(maxNbLines)),
    m_maxNbLines(maxNbLines),
    m_nbLines(0),
    m_arrayIndex(0),
    m_buffFilled(false)
{
  m_histBuffer.setAutoDelete(true);
  m_histBuffer.resize(maxNbLines);
  m_wrappedLine.resize(maxNbLines);
}

HistoryScrollBuffer::~HistoryScrollBuffer()
{
}

void HistoryScrollBuffer::addCells(ca a[], int count)
{
  //unsigned int nbLines = countLines(bytes, len);

  histline* newLine = new histline;

  newLine->duplicate(a, count);
  
  ++m_arrayIndex;
  if (m_arrayIndex >= m_maxNbLines) {
     m_arrayIndex = 0;
     m_buffFilled = true;
    }

  if (m_nbLines < m_maxNbLines - 1) ++m_nbLines;

  // m_histBuffer.remove(m_arrayIndex); // not necessary
  m_histBuffer.insert(m_arrayIndex, newLine);
  m_wrappedLine.clearBit(m_arrayIndex);
}

void HistoryScrollBuffer::normalize()
{
  if (!m_buffFilled || !m_arrayIndex) return;
  QPtrVector<histline> newHistBuffer;
  newHistBuffer.resize(m_maxNbLines);
  QBitArray newWrappedLine;
  newWrappedLine.resize(m_maxNbLines);
  for(int i = 0; i < (int) m_maxNbLines-2; i++)
  {
     int lineno = adjustLineNb(i);
     newHistBuffer.insert(i+1, m_histBuffer[lineno]);
     newWrappedLine.setBit(i+1, m_wrappedLine[lineno]);
  }
  m_histBuffer.setAutoDelete(false);
  // Qt 2.3: QVector copy assignment is buggy :-(
  //  m_histBuffer = newHistBuffer;
  for(int i = 0; i < (int) m_maxNbLines; i++)
  {
     m_histBuffer.insert(i, newHistBuffer[i]);
     m_wrappedLine.setBit(i, newWrappedLine[i]);
  }
  m_histBuffer.setAutoDelete(true);

  m_arrayIndex = m_maxNbLines;
  m_buffFilled = false;
  m_nbLines = m_maxNbLines-2;
}

void HistoryScrollBuffer::addLine(bool previousWrapped)
{
  m_wrappedLine.setBit(m_arrayIndex,previousWrapped);
}

int HistoryScrollBuffer::getLines()
{
  return m_nbLines; // m_histBuffer.size();
}

int HistoryScrollBuffer::getLineLen(int lineno)
{
  if (lineno >= (int) m_maxNbLines) return 0;

  lineno = adjustLineNb(lineno);

  histline *l = m_histBuffer[lineno];

  return l ? l->size() : 0;
}

bool HistoryScrollBuffer::isWrappedLine(int lineno)
{
  if (lineno >= (int) m_maxNbLines)
    return 0;

  return m_wrappedLine[adjustLineNb(lineno)];
}

void HistoryScrollBuffer::getCells(int lineno, int colno, int count, ca res[])
{
  if (!count) return;

  assert (lineno < (int) m_maxNbLines);

  lineno = adjustLineNb(lineno);
  
  histline *l = m_histBuffer[lineno];

  if (!l) {
    memset(res, 0, count * sizeof(ca));
    return;
  }

  assert((colno < (int) l->size()) || (count == 0));
    
  memcpy(res, l->data() + colno, count * sizeof(ca));
}

void HistoryScrollBuffer::setMaxNbLines(unsigned int nbLines)
{
  normalize();
  m_maxNbLines = nbLines;
  m_histBuffer.resize(m_maxNbLines);
  m_wrappedLine.resize(m_maxNbLines);
  if (m_nbLines > m_maxNbLines - 2)
     m_nbLines = m_maxNbLines -2;

  delete m_histType;
  m_histType = new HistoryTypeBuffer(nbLines);
}

int HistoryScrollBuffer::adjustLineNb(int lineno)
{
  if (m_buffFilled)
      return (lineno + m_arrayIndex + 2) % m_maxNbLines;
  else
      return lineno + 1;
}


// History Scroll None //////////////////////////////////////
HistoryScrollNone::HistoryScrollNone()
  : HistoryScroll(new HistoryTypeNone())
{
}

HistoryScrollNone::~HistoryScrollNone()
{
}

bool HistoryScrollNone::hasScroll()
{
  return false;
}

int  HistoryScrollNone::getLines()
{
  return 0;
}

int  HistoryScrollNone::getLineLen(int)
{
  return 0;
}

bool HistoryScrollNone::isWrappedLine(int lineno)
{
  return false;
}

void HistoryScrollNone::getCells(int, int, int, ca [])
{
}

void HistoryScrollNone::addCells(ca [], int)
{
}

void HistoryScrollNone::addLine(bool)
{
}

// History Scroll BlockArray //////////////////////////////////////
HistoryScrollBlockArray::HistoryScrollBlockArray(size_t size)
  : HistoryScroll(new HistoryTypeBlockArray(size))
{
  m_lineLengths.setAutoDelete(true);
  m_blockArray.setHistorySize(size); // nb. of lines.
}

HistoryScrollBlockArray::~HistoryScrollBlockArray()
{
}

int  HistoryScrollBlockArray::getLines()
{
  return m_lineLengths.count();
}

int  HistoryScrollBlockArray::getLineLen(int lineno)
{
  size_t *pLen = m_lineLengths[lineno];
  size_t res = pLen ? *pLen : 0;

  return res;
}

bool HistoryScrollBlockArray::isWrappedLine(int lineno)
{
  return false;
}

void HistoryScrollBlockArray::getCells(int lineno, int colno,
                                       int count, ca res[])
{
  if (!count) return;

  const Block *b = m_blockArray.at(lineno);

  if (!b) {
    memset(res, 0, count * sizeof(ca)); // still better than random data
    return;
  }

  assert(((colno + count) * sizeof(ca)) < ENTRIES);
  memcpy(res, b->data + (colno * sizeof(ca)), count * sizeof(ca));
}

void HistoryScrollBlockArray::addCells(ca a[], int count)
{
  Block *b = m_blockArray.lastBlock();
  
  if (!b) return;

  // put cells in block's data
  assert((count * sizeof(ca)) < ENTRIES);

  memset(b->data, 0, ENTRIES);

  memcpy(b->data, a, count * sizeof(ca));
  b->size = count * sizeof(ca);

  size_t res = m_blockArray.newBlock();
  assert (res > 0);

  // store line length
  size_t *pLen = new size_t;
  *pLen = count;
  
  m_lineLengths.replace(m_blockArray.getCurrent(), pLen);
}

void HistoryScrollBlockArray::addLine(bool)
{
}


//////////////////////////////////////////////////////////////////////
// History Types
//////////////////////////////////////////////////////////////////////
HistoryType::HistoryType()
{
}

HistoryType::~HistoryType()
{
}


//////////////////////////////
HistoryTypeNone::HistoryTypeNone()
{
}

bool HistoryTypeNone::isOn() const
{
  return false;
}

HistoryScroll* HistoryTypeNone::getScroll(HistoryScroll *old) const
{
  delete old;
  return new HistoryScrollNone();
}

unsigned int HistoryTypeNone::getSize() const
{
  return 0;
}


//////////////////////////////
HistoryTypeBlockArray::HistoryTypeBlockArray(size_t size)
  : m_size(size)
{
}

bool HistoryTypeBlockArray::isOn() const
{
  return true;
}

unsigned int HistoryTypeBlockArray::getSize() const
{
  return m_size;
}

HistoryScroll* HistoryTypeBlockArray::getScroll(HistoryScroll *old) const
{
  delete old;
  return new HistoryScrollBlockArray(m_size);
}


//////////////////////////////
HistoryTypeBuffer::HistoryTypeBuffer(unsigned int nbLines)
  : m_nbLines(nbLines)
{
}

bool HistoryTypeBuffer::isOn() const
{
  return true;
}

unsigned int HistoryTypeBuffer::getNbLines() const
{
  return m_nbLines;
}

unsigned int HistoryTypeBuffer::getSize() const
{
  return getNbLines();
}

HistoryScroll* HistoryTypeBuffer::getScroll(HistoryScroll *old) const
{
  if (old)
  {
    HistoryScrollBuffer *oldBuffer = dynamic_cast<HistoryScrollBuffer*>(old);
    if (oldBuffer)
    {
       oldBuffer->setMaxNbLines(m_nbLines);
       return oldBuffer;
    }

    HistoryScroll *newScroll = new HistoryScrollBuffer(m_nbLines);
    int lines = old->getLines();
    int startLine = 0;
    if (lines > (int) m_nbLines)
       startLine = lines - m_nbLines;

    ca line[LINE_SIZE];
    for(int i = startLine; i < lines; i++)
    {
       int size = old->getLineLen(i);
       if (size > LINE_SIZE)
       {
          ca *tmp_line = new ca[size];
          old->getCells(i, 0, size, tmp_line);
          newScroll->addCells(tmp_line, size);
          newScroll->addLine(old->isWrappedLine(i));
          delete tmp_line;
       }
       else
       {
          old->getCells(i, 0, size, line);
          newScroll->addCells(line, size);
          newScroll->addLine(old->isWrappedLine(i));
       }
    }
    delete old;
    return newScroll;
  }
  return new HistoryScrollBuffer(m_nbLines);
}
