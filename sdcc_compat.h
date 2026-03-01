/*
 * sdcc_compat.h — SDCC keyword compatibility stubs for IntelliSense.
 *
 * Part of JQB_CH55XPlatform:
 *   https://github.com/JAQUBA/JQB_CH55XPlatform
 *
 * This file is force-included by VS Code C/C++ extension when analyzing
 * CH55x source files.  It maps SDCC-specific keywords to standard C
 * equivalents so IntelliSense can parse the code without errors.
 *
 * During actual SDCC compilation __SDCC is predefined by the compiler
 * and this entire file is skipped — zero impact on the build.
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef __SDCC

/* Storage class qualifiers — ignored by IntelliSense */
#define __xdata
#define __data
#define __idata
#define __pdata
#define __code
#define __near
#define __far

/* Bit type — not in standard C, approximate as unsigned char */
#define __bit unsigned char

/* SFR types — map to compatible volatile C types */
#define __sfr volatile unsigned char
#define __sbit volatile unsigned char
#define __sfr16 volatile unsigned int
#define __sfr32 volatile unsigned long

/* Address attribute — stripped for IntelliSense */
#define __at(x)

/* Function/interrupt attributes — stripped for IntelliSense */
#define __interrupt(x)
#define __using(x)
#define __reentrant
#define __naked
#define __wparam
#define __critical

#endif /* __SDCC */
