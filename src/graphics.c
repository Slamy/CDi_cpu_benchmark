#include <sysio.h>
#include <ucm.h>
#include <memory.h>
#include "video.h"
#include "graphics.h"

u_char *paCursor;
u_char *pbBackground;

int curIcfA = ICF_MAX;
int curIcfB = ICF_MAX;

void fillBuffer(buffer, data, size) register u_int *buffer;
register u_int data, size;
{
	int i;
	size = size >> 2;
	for (i = 0; i < size; i++)
	{
		*buffer++ = data;
	}
}

void fillVideoBuffer(videoBuffer, data) register u_int *videoBuffer;
u_int data;
{
	fillBuffer(videoBuffer, data, VBUFFER_SIZE);
}

void createVideoBuffers()
{
	setIcf(ICF_MIN, ICF_MIN);
	paCursor = (u_char *)srqcmem(VBUFFER_SIZE, VIDEO1);
	pbBackground = (u_char *)srqcmem(VBUFFER_SIZE, VIDEO2);

	fillVideoBuffer(pbBackground, 0);
	fillTestPattern(paCursor);

	dc_wrli(videoPath, lctA, 0, 0, cp_dadr((int)paCursor + pixelStart));
	dc_wrli(videoPath, lctB, 0, 0, cp_dadr((int)pbBackground + pixelStart));
}

void fillTestPattern(target) register u_char *target;
{
	register int x, y;

	for (y = 0; y < SCREEN_HEIGHT; y++)
	{
		for (x = 0; x < SCREEN_WIDTH; x++)
		{
			*target = (x >> 1) & 0x7f;
			target++;
		}
	}
}

void setIcf(icfA, icfB) register int icfA, icfB;
{
	curIcfA = icfA > ICF_MAX ? ICF_MAX : (icfA < ICF_MIN ? ICF_MIN : icfA);
	curIcfB = icfB > ICF_MAX ? ICF_MAX : (icfB < ICF_MIN ? ICF_MIN : icfB);

	dc_wrli(videoPath, lctA, 0, 7, cp_icf(PA, curIcfA));
	dc_wrli(videoPath, lctB, 0, 7, cp_icf(PB, curIcfB));
}

void initGraphics()
{
	createVideoBuffers();
}
