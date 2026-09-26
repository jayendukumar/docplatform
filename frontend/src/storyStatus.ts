export type StoryStatus = 'implemented' | 'partial' | 'planned'

// Evidence-backed overlay for the generated source-story catalogue.
// Stories not listed here intentionally remain planned until evidence exists.
export const storyStatus: Record<string, StoryStatus> = {
  'E1-01': 'implemented', 'E1-02': 'implemented', 'E1-03': 'implemented', 'E1-04': 'implemented', 'E1-05': 'implemented', 'E1-06': 'partial', 'E1-07': 'partial', 'E1-08': 'partial', 'E1-09': 'partial', 'E1-10': 'partial', 'E1-11': 'partial', 'E1-12': 'partial',
  'E2-01': 'implemented', 'E2-02': 'implemented', 'E2-03': 'implemented', 'E2-04': 'partial', 'E2-05': 'implemented', 'E2-06': 'implemented', 'E2-07': 'partial', 'E2-08': 'partial', 'E2-09': 'partial', 'E2-10': 'partial', 'E2-11': 'partial', 'E2-12': 'partial', 'E2-13': 'partial', 'E2-14': 'partial', 'E2-15': 'partial', 'E2-16': 'partial',
  'E3-01': 'implemented', 'E3-02': 'implemented', 'E3-03': 'implemented', 'E3-04': 'implemented',
  'E3-05': 'implemented', 'E3-06': 'implemented', 'E3-07': 'implemented', 'E3-08': 'partial', 'E3-09': 'partial',
  'E4-01': 'partial', 'E4-02': 'partial', 'E4-03': 'partial', 'E4-04': 'partial', 'E4-05': 'partial',
  'E4-06': 'partial', 'E4-07': 'partial', 'E4-08': 'partial', 'E4-09': 'partial', 'E4-10': 'implemented',
  'E5-01': 'implemented', 'E5-02': 'implemented', 'E5-03': 'implemented', 'E5-04': 'implemented',
  'E5-05': 'implemented', 'E5-06': 'implemented', 'E5-07': 'implemented', 'E5-09': 'partial',
  'E14-01': 'partial', 'E14-02': 'partial', 'E14-03': 'implemented', 'E14-04': 'implemented',
  'E6-01': 'partial', 'E6-02': 'partial', 'E6-03': 'partial', 'E6-04': 'partial', 'E6-05': 'partial', 'E8-01': 'implemented', 'E8-02': 'partial', 'E8-03': 'partial', 'E8-04': 'partial', 'E8-05': 'implemented', 'E8-06': 'implemented', 'E8-07': 'implemented', 'E8-08': 'partial',
  'E9-01': 'implemented', 'E9-02': 'implemented', 'E9-03': 'implemented', 'E9-04': 'partial',
  'E9-05': 'implemented', 'E9-06': 'implemented', 'E9-07': 'implemented', 'E9-08': 'implemented', 'E9-09': 'implemented', 'E9-10': 'implemented',
  'E7-01': 'implemented', 'E7-05': 'implemented',
  'E5-08': 'implemented', 'E10-01': 'partial', 'E10-02': 'implemented', 'E10-03': 'implemented', 'E10-04': 'implemented', 'E10-05': 'implemented', 'E10-06': 'implemented',
  'E11-02': 'implemented', 'E11-03': 'implemented', 'E11-04': 'partial', 'E11-05': 'implemented',
  'E7-02': 'implemented', 'E7-03': 'implemented',
  'E7-04': 'implemented', 'E12-01': 'implemented', 'E12-02': 'partial', 'E12-03': 'implemented',
  'E13-01': 'planned', 'E13-02': 'planned', 'E13-03': 'planned',
  'E15-01': 'planned', 'E15-02': 'planned', 'E15-03': 'planned', 'E15-04': 'planned', 'E15-05': 'planned',
}

export function getStoryStatus(storyId: string): StoryStatus {
  return storyStatus[storyId] ?? 'planned'
}
